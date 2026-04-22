import os
import sys
import pickle
import traceback
import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# ── PyTorch imports ───────────────────────────────────────────────────────────
try:
    import torch
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from models.stgnn import WeatherSTGNN
    from training.data_collector import build_graph_edges
    from training.preprocess import transform_static_features
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"[ml_service] PyTorch/STGNN not available: {e}")
    traceback.print_exc()
    TORCH_AVAILABLE = False


# ── Shared constants (single source of truth) ─────────────────────────────────
try:
    from shared_config import (
        DYNAMIC_FEATURES, STATIC_FEATURES,
        CITY_NAMES, NUM_NODES,
        TIME_STEPS, FUTURE_STEPS, HIDDEN_DIM,
        MODEL_PATH, SCALER_PATH, GRAPH_THRESHOLD_KM,
    )
except ImportError:
    from backend.shared_config import (
        DYNAMIC_FEATURES, STATIC_FEATURES,
        CITY_NAMES, NUM_NODES,
        TIME_STEPS, FUTURE_STEPS, HIDDEN_DIM,
        MODEL_PATH, SCALER_PATH, GRAPH_THRESHOLD_KM,
    )


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
        self.model_path  = MODEL_PATH
        self.scaler_path = SCALER_PATH
        self.is_ready    = False
        self._load_artifacts()

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_artifacts(self):
        if not TORCH_AVAILABLE:
            print("[ml_service] PyTorch unavailable – running in API-only mode.")
            return
        if not (os.path.exists(self.model_path) and os.path.exists(self.scaler_path)):
            print("[ml_service] Model weights not found – running in API-only mode.")
            return

        try:
            print("[ml_service] Loading STGNN model and scalers …")
            device = torch.device("cpu")

            # Build model & load weights
            self.model = WeatherSTGNN(
                num_nodes=NUM_NODES,
                dynamic_features=len(DYNAMIC_FEATURES),
                static_features=len(STATIC_FEATURES),
                hidden_dim=HIDDEN_DIM
            )
            self.model.load_state_dict(
                torch.load(self.model_path, map_location=device, weights_only=True)
            )
            self.model.eval()

            # Load per-node scalers
            with open(self.scaler_path, "rb") as f:
                self.scalers = pickle.load(f)

            # Build adjacency once
            edges, _ = build_graph_edges(threshold_km=GRAPH_THRESHOLD_KM)
            self.adj  = _build_adj(edges, NUM_NODES, device)

            self.is_ready = True
            print(f"[ml_service] Ready – {NUM_NODES} nodes, {FUTURE_STEPS}h horizon.")

        except Exception:
            print("[ml_service] ERROR during artifact loading – falling back to API-only mode.")
            traceback.print_exc()
            self.is_ready = False

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_city_data(self, city_dfs: Dict[str, pd.DataFrame]) -> None:
        """
        Raises ValueError if any of the 7 expected graph nodes is missing
        or has fewer rows than TIME_STEPS. This catches data-shape mismatches
        before they cause a cryptic 500 inside the model forward pass.
        """
        missing = [c for c in CITY_NAMES if c not in city_dfs]
        if missing:
            raise ValueError(
                f"[ml_service] Data missing for {len(missing)} node(s): {missing}. "
                "Cannot form the graph tensor."
            )

        short = {
            city: len(df)
            for city, df in city_dfs.items()
            if len(df) < TIME_STEPS
        }
        if short:
            raise ValueError(
                f"[ml_service] Insufficient history rows for nodes {short}. "
                f"Need at least {TIME_STEPS} rows per node."
            )

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
            sta = transform_static_features(df).values
            data[:, i, :len(DYNAMIC_FEATURES)] = dyn
            data[:, i, len(DYNAMIC_FEATURES):]  = sta

        # Take the last TIME_STEPS rows
        window = data[-TIME_STEPS:]
        tensor = torch.FloatTensor(window).unsqueeze(0)   # [1, T, N, F]

        # ── Diagnostic 1: input shape ─────────────────────────────────────────
        print(
            f"[ml_service] Input tensor shape: {list(tensor.shape)} "
            f"(expected [1, {TIME_STEPS}, {NUM_NODES}, "
            f"{len(DYNAMIC_FEATURES) + len(STATIC_FEATURES)}])"
        )

        # ── Diagnostic 2: input variance (near-zero = static/flat input) ──────
        dyn_slice = tensor[0, :, :, :len(DYNAMIC_FEATURES)]   # [T, N, 6]
        per_feat_std = dyn_slice.std(dim=0).mean(dim=0)       # [6] mean std across nodes
        print("[ml_service] Input std per dynamic feature (0=flat, >0.01=ok):")
        for feat, std_val in zip(DYNAMIC_FEATURES, per_feat_std.tolist()):
            flag = "WARN FLAT" if std_val < 0.005 else "ok"
            print(f"  {feat:30s}: std={std_val:.4f}  {flag}")

        return tensor

    def predict(self, city_dfs: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run STGNN inference and return a dict keyed by city name.
        Each city contains a list of 48 hourly forecast dicts.
        Raises on any error so the caller (api.py) can return a proper 500.
        """
        if not self.is_ready:
            return {}

        try:
            # ── 1. Validate all 7 nodes have enough data ──────────────────────
            self.validate_city_data(city_dfs)

            # ── 2. Build graph input tensor ───────────────────────────────────
            x   = self.preprocess_graph_input(city_dfs)       # [1, T, N, F]
            adj = self.adj.unsqueeze(0)                        # [1, N, N]

            # ── Diagnostic 3: adjacency edge count ───────────────────────────
            edge_count = int((self.adj > 0).sum().item()) - NUM_NODES  # subtract self-loops
            print(f"[ml_service] Adjacency: {edge_count} directed edges "
                  f"(0 = graph is disconnected, GCN is useless!)")

            # ── 3. Forward pass ───────────────────────────────────────────────
            with torch.no_grad():
                preds = self.model(x, adj, future_steps=FUTURE_STEPS)  # [1, 48, N, 6]

            # ── Diagnostic 4: raw output diversity ───────────────────────────
            preds_np = preds.squeeze(0).numpy()   # [48, N, 6]
            raw_std   = preds_np.std(axis=0).mean()  # mean std across nodes & features over time
            print(f"[ml_service] Raw output std over 48 steps: {raw_std:.5f} "
                  f"({'WARN NEAR ZERO - model predicts constants' if raw_std < 0.001 else 'ok - predictions vary'})")
            print(f"[ml_service] Output tensor shape: {list(preds.shape)}")

            # ── 4. Inverse-transform and structure results ────────────────────
            result = {}
            for i, city in enumerate(CITY_NAMES):
                scaler     = self.scalers[city]
                city_preds = preds_np[:, i, :]                      # [48, 6]
                city_inv   = scaler.inverse_transform(city_preds)   # [48, 6]

                # Diagnostic 5: per-city output range after inverse-transform
                temp_range = city_inv[:, 0].max() - city_inv[:, 0].min()
                print(f"  [{city}] temp range after inv-transform: "
                      f"{city_inv[:,0].min():.1f}–{city_inv[:,0].max():.1f} °C  "
                      f"(spread={temp_range:.2f}°C {'WARN FLAT' if temp_range < 0.5 else 'ok'})")

                steps = []
                for h in range(FUTURE_STEPS):
                    row = city_inv[h]
                    steps.append({
                        "hour":                 h + 1,
                        "temperature_2m":       round(float(row[0]), 2),
                        "relative_humidity_2m": round(float(row[1]), 2),
                        "wind_speed_10m":       round(float(row[2]), 2),
                        "surface_pressure":     round(float(row[3]), 2),
                        "precipitation":        round(float(row[4]), 2),
                        "weather_code":         int(round(float(row[5]))),
                    })
                result[city] = steps

            return result

        except Exception:
            # Print full traceback so Docker/server logs show root cause
            print("[ml_service] ERROR during inference:")
            traceback.print_exc()
            raise   # re-raise so api.py returns a 500 with detail


# ── Singleton ──────────────────────────────────────────────────────────────────
ml_service = STGNNInferenceService()
