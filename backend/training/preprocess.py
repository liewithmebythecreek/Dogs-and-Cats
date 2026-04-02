import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pickle
import os

def preprocess_data(df: pd.DataFrame, time_steps: int = 24, future_steps: int = 24, scaler_path: str = None) -> tuple:
    """
    Cleans the dataframe (fills NaNs), scales it using MinMaxScaler,
    and converts it into sequences for LSTM training.

    Fine-tuning behaviour:
      - If `scaler_path` points to an existing file the saved scaler is LOADED
        (transform only) so that the feature scale never drifts between runs.
      - If no saved scaler exists a new one is fitted on the current data and
        saved to `scaler_path` for all future runs.

    time_steps:   The number of historical hours to use as input (X)
    future_steps: The number of future hours to predict as output (Y)
    scaler_path:  Path to save/load the MinMaxScaler pickle.
    """
    # Defensive missing value handling
    df = df.copy()
    df = df.ffill().bfill()

    features = [
        'temperature_2m', 'relative_humidity_2m',
        'wind_speed_10m', 'surface_pressure',
        'precipitation', 'weather_code'
    ]
    df = df[features]

    # ── Scaler: load existing or fit new ─────────────────────────────────────
    if scaler_path and os.path.exists(scaler_path):
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        print(f"[preprocess] Loaded existing scaler from {scaler_path}")
        scaled_data = scaler.transform(df)
    else:
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(df)
        if scaler_path:
            os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            print(f"[preprocess] New scaler fitted and saved to {scaler_path}")

    # ── Create Sequences ──────────────────────────────────────────────────────
    X, Y = [], []
    for i in range(len(scaled_data) - time_steps - future_steps):
        X.append(scaled_data[i:(i + time_steps), :])
        Y.append(scaled_data[(i + time_steps):(i + time_steps + future_steps), :])

    return np.array(X), np.array(Y)


def preprocess_inference(df: pd.DataFrame, scaler_path: str) -> np.ndarray:
    """
    For Inference/Prediction. Uses pre-saved scaler.
    Expects df with exact features in `preprocess_data`.
    """
    df = df.copy()
    df = df.ffill().bfill()
    features = [
        'temperature_2m', 'relative_humidity_2m',
        'wind_speed_10m', 'surface_pressure',
        'precipitation', 'weather_code'
    ]
    df = df[features]

    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)

    scaled_data = scaler.transform(df)
    return scaled_data  # shape: (time_steps, features)


if __name__ == "__main__":
    pass
