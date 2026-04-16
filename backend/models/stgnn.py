import torch
import torch.nn as nn
from torch_geometric.nn import DenseGCNConv


class WeatherSTGNN(nn.Module):
    """
    Spatio-Temporal Graph Neural Network for 48-hour multi-city weather forecasting.

    Architecture:
      Encoder  : Linear → ReLU  (per-node feature projection)
      Processor: 2× DenseGCNConv (spatial message-passing) + LSTMCell (temporal)
      Decoder  : Linear → ReLU → Linear → Tanh (residual prediction, bounded to [-1, 1])

    Autoregressive inference:
      - Runs the full history window through the encoder/GCN/LSTM to build hidden state.
      - Then generates `future_steps` predictions one step at a time, feeding each
        predicted delta back as the next input (residual connection).
      - Predictions are clamped to [0, 1] (MinMax-scaled space) to prevent runaway
        accumulation of residuals, which is the primary cause of flat/linear outputs.
    """

    def __init__(self, num_nodes=7, dynamic_features=6, static_features=5, hidden_dim=64):
        super().__init__()
        self.num_nodes  = num_nodes
        self.dyn_dim    = dynamic_features
        self.stat_dim   = static_features
        self.hidden_dim = hidden_dim

        in_dim = dynamic_features + static_features

        # ── Encoder ──────────────────────────────────────────────────────────
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
        )

        # ── Spatial processor ────────────────────────────────────────────────
        self.gcn1 = DenseGCNConv(hidden_dim, hidden_dim)
        self.gcn2 = DenseGCNConv(hidden_dim, hidden_dim)

        # ── Temporal processor ───────────────────────────────────────────────
        self.lstm = nn.LSTMCell(hidden_dim, hidden_dim)

        # ── Decoder ──────────────────────────────────────────────────────────
        # Output is a bounded residual in [-1, 1] via Tanh.
        # Applied to MinMax-scaled space; predictions are clamped to [0, 1] after
        # adding the residual so they never leave a physically valid range.
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, dynamic_features),
            nn.Tanh(),   # ← bounds residual to [-1, 1]; prevents linear drift
        )

    # ── Forward ──────────────────────────────────────────────────────────────

    def forward(self, x_history, adj, future_steps=48):
        """
        Args:
            x_history  : [B, T, N, F]  — scaled input history
            adj        : [B, N, N]     — normalised adjacency matrix
            future_steps: int          — number of 1-h steps to forecast
        Returns:
            [B, future_steps, N, dyn_dim] — scaled forecast
        """
        batch_size, time_steps, num_nodes, _ = x_history.shape

        # Initialise hidden / cell state
        hx = torch.zeros(batch_size * num_nodes, self.hidden_dim, device=x_history.device)
        cx = torch.zeros(batch_size * num_nodes, self.hidden_dim, device=x_history.device)

        # ── 1. Warm-up: encode the full history window ────────────────────────
        for t in range(time_steps):
            x_t = x_history[:, t, :, :]                         # [B, N, F]
            enc = self.encoder(x_t)                              # [B, N, H]
            spa = self.gcn1(enc, adj).relu()                     # [B, N, H]
            spa = self.gcn2(spa, adj).relu()                     # [B, N, H]

            spa_flat = spa.view(batch_size * num_nodes, self.hidden_dim)
            hx, cx   = self.lstm(spa_flat, (hx, cx))

        # ── 2. Autoregressive decoding ────────────────────────────────────────
        outputs = []

        # Seed: last observed step (dynamic features only, scaled)
        pred_dyn    = x_history[:, -1, :, :self.dyn_dim].clone()   # [B, N, dyn]
        stat_feat   = x_history[:, -1, :, self.dyn_dim:].clone()   # [B, N, stat]

        for _ in range(future_steps):
            current_in = torch.cat([pred_dyn, stat_feat], dim=-1)  # [B, N, F]

            enc = self.encoder(current_in)
            spa = self.gcn1(enc, adj).relu()
            spa = self.gcn2(spa, adj).relu()

            spa_flat = spa.view(batch_size * num_nodes, self.hidden_dim)
            hx, cx   = self.lstm(spa_flat, (hx, cx))

            hx_unflat = hx.view(batch_size, num_nodes, self.hidden_dim)

            # Tanh-bounded residual delta in [-1, 1] → scale down to ±0.05
            # This prevents single badly-initialised weights from dominating.
            residual = self.decoder(hx_unflat) * 0.05  # [B, N, dyn]

            pred_dyn = (pred_dyn + residual).clamp(0.0, 1.0)  # stay in scaled space
            outputs.append(pred_dyn.unsqueeze(1))              # [B, 1, N, dyn]

        return torch.cat(outputs, dim=1)   # [B, future_steps, N, dyn]
