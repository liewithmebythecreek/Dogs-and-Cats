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
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import mlflow

from .data_collector import fetch_historical_data, build_graph_edges, CITY_NAMES
from .preprocess import preprocess_data

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.stgnn import WeatherSTGNN
from shared_config import DYNAMIC_FEATURES, STATIC_FEATURES, GRAPH_THRESHOLD_KM

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
FINETUNE_LR       = 1e-3   # temporarily boosted to overcome old zeroed-out time weights
FINETUNE_DAYS     = 30     # last 30 days for fine-tuning
FINETUNE_PATIENCE = 10     # more patience for aggressive fine-tuning

MODEL_PATH  = 'backend/models/stgnn.pt'
SCALER_PATH = 'backend/models/stgnn_scaler.pkl'
MLFLOW_TRACKING_DIR = Path('backend/mlruns').resolve()
DEFAULT_MLFLOW_TRACKING_URI = MLFLOW_TRACKING_DIR.as_uri()
DEFAULT_MLFLOW_EXPERIMENT = 'WeatherSTGNN'


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_adj_matrix(edges, num_nodes, device):
    adj = torch.zeros((num_nodes, num_nodes), device=device)
    for [u, v] in edges:
        adj[u, v] = 1.0
        adj[v, u] = 1.0
    adj += torch.eye(num_nodes, device=device)
    deg  = adj.sum(dim=1, keepdim=True)
    return adj / deg


def weighted_mse_loss(
    pred,
    target,
    device,
    decay_rate=0.015,
    var_lambda=0.05,
    delta_lambda=0.35,
    curvature_lambda=0.1,
):
    """
    Time-weighted horizon loss that supervises both level and shape.
    Penalising first- and second-order differences makes a constant negative
    residual much harder for the model to hide behind over a 48-step rollout.
    """
    future_steps = pred.size(1)
    weights = torch.exp(-torch.arange(future_steps, dtype=pred.dtype, device=device) * decay_rate)
    weights = (weights / weights.mean()).view(1, future_steps, 1, 1)

    # 1. Base level loss
    mse_loss = ((pred - target) ** 2 * weights).mean()

    # 2. Match hour-to-hour changes so the decoder learns curvature instead of
    # collapsing into a constant per-step slope.
    pred_delta = pred[:, 1:] - pred[:, :-1]
    target_delta = target[:, 1:] - target[:, :-1]
    delta_loss = ((pred_delta - target_delta) ** 2 * weights[:, 1:]).mean()

    pred_curvature = pred_delta[:, 1:] - pred_delta[:, :-1]
    target_curvature = target_delta[:, 1:] - target_delta[:, :-1]
    if pred_curvature.numel() == 0:
        curvature_loss = pred.new_tensor(0.0)
    else:
        curvature_loss = ((pred_curvature - target_curvature) ** 2 * weights[:, 2:]).mean()

    # 3. Preserve overall temporal spread
    std_pred = pred.std(dim=1, unbiased=False)
    std_target = target.std(dim=1, unbiased=False)
    var_loss = torch.abs(std_target - std_pred).mean()

    total_loss = mse_loss
    total_loss += delta_lambda * delta_loss
    total_loss += curvature_lambda * curvature_loss
    total_loss += var_lambda * var_loss
    return total_loss


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


def configure_mlflow(tracking_uri: str | None, experiment_name: str | None):
    resolved_tracking_uri = tracking_uri or os.getenv('MLFLOW_TRACKING_URI', DEFAULT_MLFLOW_TRACKING_URI)
    resolved_experiment = experiment_name or os.getenv('MLFLOW_EXPERIMENT_NAME', DEFAULT_MLFLOW_EXPERIMENT)

    mlflow.set_tracking_uri(resolved_tracking_uri)
    mlflow.set_experiment(resolved_experiment)
    return resolved_tracking_uri, resolved_experiment


def build_mlflow_run_name(finetune: bool, freeze_gcn: bool, explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name

    mode = 'finetune' if finetune else 'cold-start'
    suffix = '-freeze-gcn' if freeze_gcn else ''
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return f'{mode}{suffix}-{timestamp}'


def log_mlflow_artifacts(model: WeatherSTGNN, run_config: dict, history: list[dict]):
    artifact_paths = [
        Path(__file__).resolve(),
        Path(__file__).with_name('preprocess.py').resolve(),
        Path(__file__).with_name('data_collector.py').resolve(),
        Path(__file__).resolve().parents[1] / 'models' / 'stgnn.py',
        Path(__file__).resolve().parents[1] / 'shared_config.py',
    ]

    mlflow.log_dict(run_config, 'metadata/run_config.json')
    mlflow.log_dict({'epochs': history}, 'metrics/training_history.json')
    mlflow.log_text(str(model), 'artifacts/model_architecture.txt')

    for artifact_path in artifact_paths:
        if artifact_path.exists():
            mlflow.log_artifact(str(artifact_path), artifact_path='source')

    for artifact_path, target_dir in (
        (Path(MODEL_PATH).resolve(), 'checkpoints'),
        (Path(SCALER_PATH).resolve(), 'scalers'),
    ):
        if artifact_path.exists():
            mlflow.log_artifact(str(artifact_path), artifact_path=target_dir)


# ── Main ──────────────────────────────────────────────────────────────────────

def train_and_evaluate(
    finetune: bool,
    epochs: int,
    freeze_gcn: bool,
    mlflow_tracking_uri: str | None = None,
    mlflow_experiment_name: str | None = None,
    mlflow_run_name: str | None = None,
):
    # CPU threading
    num_cores = os.cpu_count() or 4
    torch.set_num_threads(num_cores)
    device = torch.device('cpu')
    print(f"[train] Using CPU with {num_cores} threads.")

    os.makedirs('backend/models', exist_ok=True)
    resolved_tracking_uri, resolved_experiment = configure_mlflow(
        tracking_uri=mlflow_tracking_uri,
        experiment_name=mlflow_experiment_name,
    )
    run_name = build_mlflow_run_name(
        finetune=finetune,
        freeze_gcn=freeze_gcn,
        explicit_name=mlflow_run_name,
    )
    print(f"[train] MLflow -> {resolved_experiment} @ {resolved_tracking_uri}")

    # ── Data window ───────────────────────────────────────────────────────────
    end   = datetime.date.today() - datetime.timedelta(days=2)
    start = end - datetime.timedelta(days=FINETUNE_DAYS if finetune else COLD_START_DAYS)
    print(f"[train] Mode={'FINE-TUNE' if finetune else 'COLD START'} | "
          f"Data: {start} -> {end} | Epochs: {epochs}")

    # ── Fetch & preprocess ────────────────────────────────────────────────────
    city_data = fetch_historical_data(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    print(f"[train] Fetched {len(city_data)} cities.")

    # Fine-tuning reuses the serving scaler, but a cold start must refit it
    # instead of inheriting stale feature ranges from an old run.
    effective_scaler_path = SCALER_PATH
    X, Y = preprocess_data(
        city_data,
        time_steps=TIME_STEPS,
        future_steps=FUTURE_STEPS,
        scaler_path=effective_scaler_path,
        reuse_existing_scaler=finetune,
    )
    print(f"[train] Preprocessed  X:{X.shape}  Y:{Y.shape}")

    # ── Adjacency matrix ──────────────────────────────────────────────────────
    edges, _ = build_graph_edges(threshold_km=GRAPH_THRESHOLD_KM)
    adj      = create_adj_matrix(edges, NUM_NODES, device)
    print(f"[train] Graph: {len(edges)} directed edges across {NUM_NODES} nodes.")

    # ── Train / val split ─────────────────────────────────────────────────────
    if len(X) < 2:
        raise ValueError(
            f"[train] Need at least 2 supervised windows after preprocessing, got {len(X)}."
        )

    split        = max(1, min(len(X) - 1, int(0.8 * len(X))))
    train_samples = split
    val_samples = len(X) - split
    train_loader = DataLoader(TensorDataset(X[:split], Y[:split]),
                              batch_size=32, shuffle=True)
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
    best_epoch       = 0
    history          = []
    run_config = {
        'mode': 'finetune' if finetune else 'cold_start',
        'dates': {
            'start': start.isoformat(),
            'end': end.isoformat(),
        },
        'tracking': {
            'experiment_name': resolved_experiment,
            'tracking_uri': resolved_tracking_uri,
            'run_name': run_name,
        },
        'data': {
            'cities': CITY_NAMES,
            'dynamic_features': DYNAMIC_FEATURES,
            'static_features': STATIC_FEATURES,
            'time_steps': TIME_STEPS,
            'future_steps': FUTURE_STEPS,
            'total_windows': len(X),
            'train_windows': train_samples,
            'val_windows': val_samples,
            'graph_edges': len(edges),
            'graph_threshold_km': GRAPH_THRESHOLD_KM,
            'reuse_existing_scaler': finetune,
        },
        'model': {
            'hidden_dim': HIDDEN_DIM,
            'num_nodes': NUM_NODES,
            'dynamic_feature_count': FEATURES,
            'static_feature_count': STATIC_FEAT,
            'freeze_gcn': freeze_gcn,
        },
        'optimization': {
            'epochs_requested': epochs,
            'learning_rate': lr,
            'patience': patience,
            'batch_size': 32,
            'num_cores': num_cores,
            'loss': {
                'decay_rate': 0.015,
                'var_lambda': 0.05,
                'delta_lambda': 0.35,
                'curvature_lambda': 0.1,
            },
        },
        'artifacts': {
            'model_path': str(Path(MODEL_PATH).resolve()),
            'scaler_path': str(Path(SCALER_PATH).resolve()),
        },
    }

    print(f"[train] LR={lr}  patience={patience}")
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tags({
            'stage': 'training',
            'mode': 'finetune' if finetune else 'cold_start',
            'model_class': 'WeatherSTGNN',
            'framework': 'pytorch',
            'freeze_gcn': str(freeze_gcn).lower(),
        })
        mlflow.log_params({
            'epochs_requested': epochs,
            'learning_rate': lr,
            'patience': patience,
            'batch_size': 32,
            'num_cores': num_cores,
            'time_steps': TIME_STEPS,
            'future_steps': FUTURE_STEPS,
            'num_nodes': NUM_NODES,
            'hidden_dim': HIDDEN_DIM,
            'dynamic_feature_count': FEATURES,
            'static_feature_count': STATIC_FEAT,
            'graph_edges': len(edges),
            'graph_threshold_km': GRAPH_THRESHOLD_KM,
            'total_windows': len(X),
            'train_windows': train_samples,
            'val_windows': val_samples,
            'reuse_existing_scaler': finetune,
        })
        mlflow.log_param('start_date', start.isoformat())
        mlflow.log_param('end_date', end.isoformat())

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
            marker   = " [BEST]" if improved else ""
            print(f"  Epoch {epoch:02d}/{epochs} | "
                  f"train={train_loss:.6f}  val={val_loss:.6f}{marker}")

            history.append({
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                'is_best': improved,
            })
            mlflow.log_metrics({
                'train_loss': train_loss,
                'val_loss': val_loss,
                'best_val_loss_so_far': min(best_val_loss, val_loss),
            }, step=epoch)

            if improved:
                best_val_loss = val_loss
                best_epoch = epoch
                patience_counter = 0
                torch.save(model.state_dict(), MODEL_PATH)
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"[train] Early stopping at epoch {epoch} (patience={patience}).")
                    break

        mlflow.log_metrics({
            'best_val_loss': best_val_loss,
            'best_epoch': best_epoch,
            'epochs_completed': len(history),
        })
        log_mlflow_artifacts(model=model, run_config=run_config, history=history)

    print(f"[train] Done. Best val loss: {best_val_loss:.6f}")
    print(f"[train] Weights -> {MODEL_PATH}")
    print(f"[train] Scalers -> {SCALER_PATH}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NeuralWeather STGNN trainer')
    parser.add_argument('--finetune',   action='store_true',
                        help='Load existing weights and fine-tune (lower LR, tight patience)')
    parser.add_argument('--epochs',     type=int, default=None,
                        help='Override epoch count (default: 50 cold / 10 fine-tune)')
    parser.add_argument('--freeze-gcn', action='store_true',
                        help='Freeze GCN spatial layers, only train LSTM + decoder')
    parser.add_argument('--mlflow-tracking-uri', type=str, default=None,
                        help='Override MLflow tracking URI (default: backend/mlruns or $MLFLOW_TRACKING_URI)')
    parser.add_argument('--mlflow-experiment', type=str, default=None,
                        help='Override MLflow experiment name (default: WeatherSTGNN or $MLFLOW_EXPERIMENT_NAME)')
    parser.add_argument('--mlflow-run-name', type=str, default=None,
                        help='Optional MLflow run name')
    args = parser.parse_args()

    effective_epochs = args.epochs or (FINETUNE_EPOCHS if args.finetune else COLD_START_EPOCHS)

    train_and_evaluate(
        finetune=args.finetune,
        epochs=effective_epochs,
        freeze_gcn=args.freeze_gcn,
        mlflow_tracking_uri=args.mlflow_tracking_uri,
        mlflow_experiment_name=args.mlflow_experiment,
        mlflow_run_name=args.mlflow_run_name,
    )
