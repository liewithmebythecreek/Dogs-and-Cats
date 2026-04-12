import os
import sys
import pickle
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# ── PyTorch imports ───────────────────────────────────────────────────────────
try:
    import torch
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from models.stgnn import WeatherSTGNN
    from training.data_collector import CITIES, CITY_NAMES, NUM_NODES, build_graph_edges
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"[ml_service] PyTorch/STGNN not available: {e}")
    TORCH_AVAILABLE = False

DYNAMIC_FEATURES = [
    'temperature_2m', 'relative_humidity_2m',
    'wind_speed_10m', 'surface_pressure',
    'precipitation', 'weather_code'
]
STATIC_FEATURES = ['sin_hour', 'cos_hour', 'elevation', 'lat', 'lon']
TIME_STEPS  = 48
FUTURE_STEPS = 48
HIDDEN_DIM  = 64


def _build_adj(edges, num_nodes, device):
    adj = torch.zeros((num_nodes, num_nodes), device=device)
    for [u, v] in edges:
        adj[u, v] = 1.0
        adj[v, u] = 1.0
    adj += torch.eye(num_nodes, device=device)
    deg  = adj.sum(dim=1, keepdim=True)
    return adj / deg


class STGNNInferenceService:
    """
    Singleton PyTorch Graph-LSTM inference service.
    The model is loaded once at startup and reused across all requests.
    """
    def __init__(self):
        self.model       = None
        self.scalers     = None   # dict[city -> MinMaxScaler]
        self.adj         = None   # pre-built adjacency tensor
        self.model_path  = "backend/models/stgnn.pt"
        self.scaler_path = "backend/models/stgnn_scaler.pkl"
        self.is_ready    = False
        self._load_artifacts()

    # ── Private ──────────────────────────────────────────────────────────────

    def _load_artifacts(self):
        if not TORCH_AVAILABLE:
            print("[ml_service] PyTorch unavailable – running in API-only mode.")
            return
        if not (os.path.exists(self.model_path) and os.path.exists(self.scaler_path)):
            print("[ml_service] Model weights not found – running in API-only mode.")
            return

        print("[ml_service] Loading STGNN model and scalers …")
        device = torch.device("cpu")

        # Build model & load weights
        self.model = WeatherSTGNN(
            num_nodes=NUM_NODES,
            dynamic_features=len(DYNAMIC_FEATURES),
            static_features=len(STATIC_FEATURES),
            hidden_dim=HIDDEN_DIM
        )
        self.model.load_state_dict(torch.load(self.model_path, map_location=device, weights_only=True))
        self.model.eval()

        # Load per-node scalers
        with open(self.scaler_path, "rb") as f:
            self.scalers = pickle.load(f)

        # Build adjacency once
        edges, _ = build_graph_edges(threshold_km=200.0)
        self.adj  = _build_adj(edges, NUM_NODES, device)

        self.is_ready = True
        print(f"[ml_service] Ready – {NUM_NODES} nodes, {FUTURE_STEPS}h horizon.")

    # ── Public API ────────────────────────────────────────────────────────────

    def preprocess_graph_input(self, city_dfs: Dict[str, pd.DataFrame]) -> "torch.Tensor":
        """
        Convert 7 DataFrames of hourly history into a [1, TIME_STEPS, N, F] tensor.
        """
        length = min(len(df) for df in city_dfs.values())
        data   = np.zeros((length, NUM_NODES, len(DYNAMIC_FEATURES) + len(STATIC_FEATURES)))

        for i, city in enumerate(CITY_NAMES):
            df = city_dfs[city].copy().iloc[-length:]
            df = df.ffill().bfill()

            dyn = self.scalers[city].transform(df[DYNAMIC_FEATURES])
            sta = df[STATIC_FEATURES].values
            data[:, i, :len(DYNAMIC_FEATURES)] = dyn
            data[:, i, len(DYNAMIC_FEATURES):]  = sta

        # Take the last TIME_STEPS rows
        window = data[-TIME_STEPS:]
        return torch.FloatTensor(window).unsqueeze(0)   # [1, T, N, F]

    def predict(self, city_dfs: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run STGNN inference and return a dict keyed by city name.
        Each city contains a list of 48 hourly forecast dicts.
        """
        if not self.is_ready:
            return {}

        x = self.preprocess_graph_input(city_dfs)           # [1, T, N, F]
        adj = self.adj.unsqueeze(0)                          # [1, N, N]

        with torch.no_grad():
            preds = self.model(x, adj, future_steps=FUTURE_STEPS)  # [1, 48, N, 6]

        preds_np = preds.squeeze(0).numpy()                  # [48, N, 6]

        result = {}
        for i, city in enumerate(CITY_NAMES):
            scaler    = self.scalers[city]
            city_preds = preds_np[:, i, :]                   # [48, 6]
            city_inv   = scaler.inverse_transform(city_preds) # [48, 6]

            steps = []
            for h in range(FUTURE_STEPS):
                row = city_inv[h]
                steps.append({
                    "hour":                h + 1,
                    "temperature_2m":      round(float(row[0]), 2),
                    "relative_humidity_2m": round(float(row[1]), 2),
                    "wind_speed_10m":       round(float(row[2]), 2),
                    "surface_pressure":     round(float(row[3]), 2),
                    "precipitation":        round(float(row[4]), 2),
                    "weather_code":         int(round(float(row[5]))),
                })
            result[city] = steps

        return result


# ── Singleton ─────────────────────────────────────────────────────────────────
ml_service = STGNNInferenceService()
