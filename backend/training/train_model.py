import os
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

from .data_collector import fetch_historical_data, build_graph_edges
from .preprocess import preprocess_data
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.stgnn import WeatherSTGNN

# ── Hyper-parameters ──────────────────────────────────────────────────────────
TIME_STEPS    = 48
FUTURE_STEPS  = 48
FEATURES      = 6   
STATIC_FEAT   = 5
HIDDEN_DIM    = 64

COLD_START_EPOCHS  = 50
COLD_START_LR      = 1e-3

FINETUNE_DAYS      = 14  
FINETUNE_EPOCHS    = 10
FINETUNE_LR        = 1e-4

def create_adj_matrix(edges, num_nodes, device):
    adj = torch.zeros((num_nodes, num_nodes), device=device)
    for [u, v] in edges:
        adj[u, v] = 1.0
        adj[v, u] = 1.0 # undirected
    adj += torch.eye(num_nodes, device=device)
    deg = adj.sum(dim=1, keepdim=True)
    adj = adj / deg
    return adj

def weighted_mse_loss(pred, target, device, decay_rate=0.05):
    future_steps = pred.size(1)
    weights = torch.exp(-torch.arange(future_steps, dtype=torch.float32) * decay_rate).to(device)
    weights = weights / weights.sum() * future_steps 
    
    weights = weights.view(1, future_steps, 1, 1)
    
    loss = (pred - target) ** 2
    loss = loss * weights
    return loss.mean()

def train_and_evaluate():
    num_cores = os.cpu_count() or 4
    torch.set_num_threads(num_cores)
    print(f"Optimizing PyTorch for CPU using {num_cores} threads")
    
    device = torch.device('cpu')
    
    os.makedirs('backend/models', exist_ok=True)
    model_path  = 'backend/models/stgnn.pt'
    scaler_path = 'backend/models/stgnn_scaler.pkl'

    end   = datetime.date.today() - datetime.timedelta(days=2)
    is_cold_start = not os.path.exists(model_path)

    if is_cold_start:
        print("=== COLD START: no existing model found - training from scratch ===")
        start  = end - datetime.timedelta(days=365) # 1 year
        epochs = COLD_START_EPOCHS
        lr     = COLD_START_LR
    else:
        print("=== FINE-TUNE: existing model found - continuing from saved weights ===")
        start  = end - datetime.timedelta(days=FINETUNE_DAYS)
        epochs = FINETUNE_EPOCHS
        lr     = FINETUNE_LR

    print(f"Fetching data  {start}  ->  {end}")
    city_data = fetch_historical_data(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    print(f"Fetched {len(city_data)} cities")

    print('Preprocessing...')
    X, Y = preprocess_data(city_data, time_steps=TIME_STEPS, future_steps=FUTURE_STEPS, scaler_path=scaler_path)
    print(f"  X: {X.shape}  |  Y: {Y.shape}")

    split = int(0.8 * len(X))
    train_dataset = TensorDataset(X[:split], Y[:split])
    val_dataset   = TensorDataset(X[split:], Y[split:])

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=False)
    val_loader   = DataLoader(val_dataset, batch_size=32, shuffle=False)

    num_nodes = len(city_data)
    model = WeatherSTGNN(num_nodes=num_nodes, dynamic_features=FEATURES, static_features=STATIC_FEAT, hidden_dim=HIDDEN_DIM)
    model.to(device)

    if not is_cold_start:
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
        print(f"  Loaded model from {model_path}")

    optimizer = optim.Adam(model.parameters(), lr=lr)

    edges, _ = build_graph_edges(threshold_km=200.0)
    single_adj = create_adj_matrix(edges, num_nodes, device)

    best_val_loss = float('inf')
    patience_counter = 0
    patience = 5 if is_cold_start else 3

    print(f'Training ({epochs} max epochs, LR={lr}) ...')
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            adj = single_adj.unsqueeze(0).expand(batch_x.size(0), -1, -1)
            
            optimizer.zero_grad()
            preds = model(batch_x, adj, future_steps=FUTURE_STEPS)
            loss = weighted_mse_loss(preds, batch_y, device)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss /= len(train_loader.dataset)
        
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                adj = single_adj.unsqueeze(0).expand(batch_x.size(0), -1, -1)
                preds = model(batch_x, adj, future_steps=FUTURE_STEPS)
                loss = weighted_mse_loss(preds, batch_y, device)
                val_loss += loss.item() * batch_x.size(0)
                
        val_loss /= len(val_loader.dataset)
        print(f"Epoch {epoch+1:02d} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), model_path)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print("Early stopping triggered.")
                break

    print(f"Eval completed. Best Val Loss: {best_val_loss:.6f}")
    print(f"Model saved to {model_path}")
    print(f"Scalers at     {scaler_path}")

if __name__ == '__main__':
    train_and_evaluate()
