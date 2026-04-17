"""
backend/training/train_model.py
Supports two modes:
  Cold start  : python -m backend.training.train_model
  Fine-tuning : python -m backend.training.train_model --finetune [--epochs N] [--freeze-gcn]
"""

import os
import sys
import argparse
import datetime
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

from .data_collector import fetch_historical_data, build_graph_edges, CITY_NAMES
from .preprocess import preprocess_data

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.stgnn import WeatherSTGNN

# ── Hyper-parameters ──────────────────────────────────────────────────────────
TIME_STEPS   = 48
FUTURE_STEPS = 48
FEATURES     = 6
STATIC_FEAT  = 5
HIDDEN_DIM   = 64
NUM_NODES    = 7

COLD_START_EPOCHS = 50
COLD_START_LR     = 1e-3
COLD_START_DAYS   = 365    # 1 year of history

FINETUNE_EPOCHS   = 10     # overridden by --epochs
FINETUNE_LR       = 1e-5   # 100× lower than cold-start to prevent catastrophic forgetting
FINETUNE_DAYS     = 30     # last 30 days for fine-tuning
FINETUNE_PATIENCE = 3      # tight early stopping for fine-tuning

MODEL_PATH  = 'backend/models/stgnn.pt'
SCALER_PATH = 'backend/models/stgnn_scaler.pkl'


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_adj_matrix(edges, num_nodes, device):
    adj = torch.zeros((num_nodes, num_nodes), device=device)
    for [u, v] in edges:
        adj[u, v] = 1.0
        adj[v, u] = 1.0
    adj += torch.eye(num_nodes, device=device)
    deg  = adj.sum(dim=1, keepdim=True)
    return adj / deg


def weighted_mse_loss(pred, target, device, decay_rate=0.05, var_lambda=0.1):
    """
    Time-Weighted MSE + Temporal Variance Loss.
    Encourages maintaining structural variance (wiggles) instead of a flat mean.
    """
    future_steps = pred.size(1)
    weights = torch.exp(
        -torch.arange(future_steps, dtype=torch.float32) * decay_rate
    ).to(device)
    weights = (weights / weights.sum()) * future_steps
    weights = weights.view(1, future_steps, 1, 1)
    
    # 1. Base MSE
    mse_loss = ((pred - target) ** 2 * weights).mean()
    
    # 2. Temporal Variance Loss
    # Standard deviation over the time dimension (dim=1)
    std_pred   = pred.std(dim=1)
    std_target = target.std(dim=1)
    var_loss   = var_lambda * torch.abs(std_target - std_pred).mean()
    
    return mse_loss + var_loss


def freeze_gcn_layers(model: WeatherSTGNN):
    """
    Freeze the spatial (GCN) layers and only let the LSTM + decoder
    parameters update. Useful when the graph topology hasn't changed
    but the temporal dynamics have shifted.
    """
    for name, param in model.named_parameters():
        if 'gcn' in name:
            param.requires_grad = False
    frozen = [n for n, p in model.named_parameters() if not p.requires_grad]
    print(f"[train] Frozen {len(frozen)} GCN parameter tensors.")
    return model


# ── Main ──────────────────────────────────────────────────────────────────────

def train_and_evaluate(finetune: bool, epochs: int, freeze_gcn: bool):
    # CPU threading
    num_cores = os.cpu_count() or 4
    torch.set_num_threads(num_cores)
    device = torch.device('cpu')
    print(f"[train] Using CPU with {num_cores} threads.")

    os.makedirs('backend/models', exist_ok=True)

    # ── Data window ───────────────────────────────────────────────────────────
    end   = datetime.date.today() - datetime.timedelta(days=2)
    start = end - datetime.timedelta(days=FINETUNE_DAYS if finetune else COLD_START_DAYS)
    print(f"[train] Mode={'FINE-TUNE' if finetune else 'COLD START'} | "
          f"Data: {start} → {end} | Epochs: {epochs}")

    # ── Fetch & preprocess ────────────────────────────────────────────────────
    city_data = fetch_historical_data(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    print(f"[train] Fetched {len(city_data)} cities.")

    # Fine-tuning REUSES the existing scaler — never refit it on new data.
    # This is the key to preventing Training-Serving Skew.
    effective_scaler_path = SCALER_PATH if finetune else SCALER_PATH
    X, Y = preprocess_data(
        city_data,
        time_steps=TIME_STEPS,
        future_steps=FUTURE_STEPS,
        scaler_path=effective_scaler_path,
    )
    print(f"[train] Preprocessed  X:{X.shape}  Y:{Y.shape}")

    # ── Adjacency matrix ──────────────────────────────────────────────────────
    edges, _ = build_graph_edges(threshold_km=200.0)
    adj      = create_adj_matrix(edges, NUM_NODES, device)
    print(f"[train] Graph: {len(edges)} directed edges across {NUM_NODES} nodes.")

    # ── Train / val split ─────────────────────────────────────────────────────
    split        = int(0.8 * len(X))
    train_loader = DataLoader(TensorDataset(X[:split], Y[:split]),
                              batch_size=32, shuffle=False)
    val_loader   = DataLoader(TensorDataset(X[split:], Y[split:]),
                              batch_size=32, shuffle=False)

    # ── Model ─────────────────────────────────────────────────────────────────
    model = WeatherSTGNN(
        num_nodes=NUM_NODES,
        dynamic_features=FEATURES,
        static_features=STATIC_FEAT,
        hidden_dim=HIDDEN_DIM,
    ).to(device)

    if finetune:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"--finetune requested but no weights found at {MODEL_PATH}. "
                "Run a cold-start first."
            )
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=False))
        print(f"[train] Loaded existing weights from {MODEL_PATH}.")

        if freeze_gcn:
            model = freeze_gcn_layers(model)
    else:
        print("[train] Cold start — training from random initialisation.")

    lr        = FINETUNE_LR if finetune else COLD_START_LR
    patience  = FINETUNE_PATIENCE if finetune else 5
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
    )

    # ── Training loop ─────────────────────────────────────────────────────────
    best_val_loss    = float('inf')
    patience_counter = 0

    print(f"[train] LR={lr}  patience={patience}")
    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            batch_adj = adj.unsqueeze(0).expand(bx.size(0), -1, -1)
            optimizer.zero_grad()
            loss = weighted_mse_loss(model(bx, batch_adj, future_steps=FUTURE_STEPS), by, device)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * bx.size(0)
        train_loss /= len(train_loader.dataset)

        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                batch_adj = adj.unsqueeze(0).expand(bx.size(0), -1, -1)
                val_loss += weighted_mse_loss(
                    model(bx, batch_adj, future_steps=FUTURE_STEPS), by, device
                ).item() * bx.size(0)
        val_loss /= len(val_loader.dataset)

        improved = val_loss < best_val_loss
        marker   = " ✓ best" if improved else ""
        print(f"  Epoch {epoch:02d}/{epochs} | "
              f"train={train_loss:.6f}  val={val_loss:.6f}{marker}")

        if improved:
            best_val_loss    = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), MODEL_PATH)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[train] Early stopping at epoch {epoch} (patience={patience}).")
                break

    print(f"[train] Done. Best val loss: {best_val_loss:.6f}")
    print(f"[train] Weights → {MODEL_PATH}")
    print(f"[train] Scalers → {SCALER_PATH}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NeuralWeather STGNN trainer')
    parser.add_argument('--finetune',   action='store_true',
                        help='Load existing weights and fine-tune (lower LR, tight patience)')
    parser.add_argument('--epochs',     type=int, default=None,
                        help='Override epoch count (default: 50 cold / 10 fine-tune)')
    parser.add_argument('--freeze-gcn', action='store_true',
                        help='Freeze GCN spatial layers, only train LSTM + decoder')
    args = parser.parse_args()

    effective_epochs = args.epochs or (FINETUNE_EPOCHS if args.finetune else COLD_START_EPOCHS)

    train_and_evaluate(
        finetune=args.finetune,
        epochs=effective_epochs,
        freeze_gcn=args.freeze_gcn,
    )
