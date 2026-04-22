"""
backend/shared_config.py
Single source of truth for all constants shared between:
  - training/preprocess.py     (training pipeline)
  - app/services/ml_service.py (inference pipeline)
  - training/train_model.py    (model architecture)
  - monitor.py                  (drift detection)

Importing from here guarantees Training-Serving Skew cannot occur due
to a constant being defined differently in two files.
"""

# ── Feature lists (order matters — must match scaler fit order) ───────────────
DYNAMIC_FEATURES = [
    'temperature_2m',
    'relative_humidity_2m',
    'wind_speed_10m',
    'surface_pressure',
    'precipitation',
    'weather_code',
]

STATIC_FEATURES = [
    'sin_hour',
    'cos_hour',
    'elevation',
    'lat',
    'lon',
]

# ── Model / graph dimensions ───────────────────────────────────────────────────
NUM_NODES     = 7
HIDDEN_DIM    = 64
TIME_STEPS    = 48   # hours of history fed into the model
FUTURE_STEPS  = 48   # hours of forecast produced

# ── City graph ────────────────────────────────────────────────────────────────
CITIES = {
    "Ropar":      {"lat": 30.9750, "lon": 76.5273, "elevation": 260},
    "Chandigarh": {"lat": 30.7333, "lon": 76.7794, "elevation": 321},
    "Ludhiana":   {"lat": 30.9010, "lon": 75.8573, "elevation": 242},
    "Patiala":    {"lat": 30.3398, "lon": 76.3869, "elevation": 250},
    "Jalandhar":  {"lat": 31.3260, "lon": 75.5762, "elevation": 228},
    "Ambala":     {"lat": 30.3782, "lon": 76.7767, "elevation": 264},
    "Shimla":     {"lat": 31.1048, "lon": 77.1734, "elevation": 2276},
}
CITY_NAMES = list(CITIES.keys())

# ── Graph edge threshold ───────────────────────────────────────────────────────
GRAPH_THRESHOLD_KM = 200.0   # cities within this distance get an edge

# ── Artifact paths (absolute based on this file's location) ───────────────────
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE_DIR, 'models', 'stgnn.pt')
SCALER_PATH = os.path.join(BASE_DIR, 'models', 'stgnn_scaler.pkl')

# ── Open-Meteo API ────────────────────────────────────────────────────────────
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
