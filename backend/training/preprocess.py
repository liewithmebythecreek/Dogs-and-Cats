import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pickle
import os
import sys
import torch

# ── Shared constants (single source of truth) ─────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared_config import CITIES, DYNAMIC_FEATURES, STATIC_FEATURES


CYCLICAL_STATIC_FEATURES = ('sin_hour', 'cos_hour')
GEOGRAPHIC_STATIC_FEATURES = tuple(
    feature for feature in STATIC_FEATURES if feature not in CYCLICAL_STATIC_FEATURES
)
GEOGRAPHIC_STATIC_RANGES = {
    feature: (
        min(city_info[feature] for city_info in CITIES.values()),
        max(city_info[feature] for city_info in CITIES.values()),
    )
    for feature in GEOGRAPHIC_STATIC_FEATURES
}


def transform_static_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preserve the cyclical time channels in sine/cosine space and min-max scale
    the geographic features so they do not swamp the dynamic inputs.
    """
    static = df[STATIC_FEATURES].copy()

    for feature in GEOGRAPHIC_STATIC_FEATURES:
        min_val, max_val = GEOGRAPHIC_STATIC_RANGES[feature]
        denom = max_val - min_val
        if denom == 0:
            static[feature] = 0.0
        else:
            static[feature] = (static[feature] - min_val) / denom

    return static.astype(np.float32)

def preprocess_data(
    city_data: dict,
    time_steps: int = 48,
    future_steps: int = 48,
    scaler_path: str = None,
    reuse_existing_scaler: bool = True,
) -> tuple:
    cities = list(city_data.keys())
    num_nodes = len(cities)
    
    should_load_existing_scaler = (
        reuse_existing_scaler and scaler_path and os.path.exists(scaler_path)
    )

    if should_load_existing_scaler:
        with open(scaler_path, 'rb') as f:
            scalers = pickle.load(f)
        print(f"[preprocess] Loaded {len(scalers)} scalers from {scaler_path}")
    else:
        scalers = {city: MinMaxScaler() for city in cities}
        for city in cities:
            df = city_data[city].copy()
            df = df.ffill().bfill()
            if len(df) > 0:
                scalers[city].fit(df[DYNAMIC_FEATURES])
            
        if scaler_path:
            os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
            with open(scaler_path, 'wb') as f:
                pickle.dump(scalers, f)
            print(f"[preprocess] Scalers fitted and saved to {scaler_path}")
    length = min([len(city_data[c]) for c in cities])
    num_windows = length - time_steps - future_steps + 1
    if num_windows <= 0:
        raise ValueError(
            f"[preprocess] Need at least {time_steps + future_steps} rows per city, got {length}."
        )

    full_data = np.zeros((length, num_nodes, len(DYNAMIC_FEATURES) + len(STATIC_FEATURES)))
    
    for i, city in enumerate(cities):
        df = city_data[city].copy().iloc[:length]
        df = df.ffill().bfill()
        
        if length > 0:
            dyn_scaled = scalers[city].transform(df[DYNAMIC_FEATURES])
            stat_data = transform_static_features(df).values
            
            full_data[:, i, :len(DYNAMIC_FEATURES)] = dyn_scaled
            full_data[:, i, len(DYNAMIC_FEATURES):] = stat_data

    X, Y = [], []
    for i in range(num_windows):
        X.append(full_data[i:(i + time_steps), :, :])
        Y.append(full_data[(i + time_steps):(i + time_steps + future_steps), :, :len(DYNAMIC_FEATURES)])

    return torch.FloatTensor(np.array(X)), torch.FloatTensor(np.array(Y))
