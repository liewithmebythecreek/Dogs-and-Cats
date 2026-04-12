import torch
import torch.nn as nn
from torch_geometric.nn import DenseGCNConv

class WeatherSTGNN(nn.Module):
    def __init__(self, num_nodes=7, dynamic_features=6, static_features=5, hidden_dim=64):
        super(WeatherSTGNN, self).__init__()
        self.num_nodes = num_nodes
        self.dyn_dim = dynamic_features
        self.stat_dim = static_features
        in_dim = dynamic_features + static_features
        self.hidden_dim = hidden_dim
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Processor: Spatial
        self.gcn1 = DenseGCNConv(hidden_dim, hidden_dim)
        self.gcn2 = DenseGCNConv(hidden_dim, hidden_dim)
        
        # Processor: Temporal
        self.lstm = nn.LSTMCell(hidden_dim, hidden_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, dynamic_features)
        )
        
    def forward(self, x_history, adj, future_steps=48):
        batch_size, time_steps, num_nodes, _ = x_history.shape
        
        hx = torch.zeros(batch_size * num_nodes, self.hidden_dim, device=x_history.device)
        cx = torch.zeros(batch_size * num_nodes, self.hidden_dim, device=x_history.device)
        
        for t in range(time_steps):
            x_t = x_history[:, t, :, :]
            enc = self.encoder(x_t)
            spatial = self.gcn1(enc, adj).relu()
            spatial = self.gcn2(spatial, adj).relu()
            
            spatial_flat = spatial.view(batch_size * num_nodes, self.hidden_dim)
            hx, cx = self.lstm(spatial_flat, (hx, cx))
        
        outputs = []
        last_x = x_history[:, -1, :, :].clone()
        pred_dyn = last_x[:, :, :self.dyn_dim]
        stat_features = last_x[:, :, self.dyn_dim:]
        
        for _ in range(future_steps):
            current_in = torch.cat([pred_dyn, stat_features], dim=-1)
            enc = self.encoder(current_in)
            spatial = self.gcn1(enc, adj).relu()
            spatial = self.gcn2(spatial, adj).relu()
            
            spatial_flat = spatial.view(batch_size * num_nodes, self.hidden_dim)
            hx, cx = self.lstm(spatial_flat, (hx, cx))
            
            hx_unflat = hx.view(batch_size, num_nodes, self.hidden_dim)
            residual = self.decoder(hx_unflat)
            
            # Predict residual (delta)
            pred_dyn = pred_dyn + residual
            outputs.append(pred_dyn.unsqueeze(1))
            
        return torch.cat(outputs, dim=1)
