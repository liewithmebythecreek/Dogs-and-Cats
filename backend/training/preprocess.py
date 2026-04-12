import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pickle
import os
import torch

DYNAMIC_FEATURES = [
    'temperature_2m', 'relative_humidity_2m',
    'wind_speed_10m', 'surface_pressure',
    'precipitation', 'weather_code'
]
STATIC_FEATURES = ['sin_hour', 'cos_hour', 'elevation', 'lat', 'lon']

def preprocess_data(city_data: dict, time_steps: int = 48, future_steps: int = 48, scaler_path: str = None) -> tuple:
    cities = list(city_data.keys())
    num_nodes = len(cities)
    
    if scaler_path and os.path.exists(scaler_path):
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
    full_data = np.zeros((length, num_nodes, len(DYNAMIC_FEATURES) + len(STATIC_FEATURES)))
    
    for i, city in enumerate(cities):
        df = city_data[city].copy().iloc[:length]
        df = df.ffill().bfill()
        
        if length > 0:
            dyn_scaled = scalers[city].transform(df[DYNAMIC_FEATURES])
            stat_data = df[STATIC_FEATURES].values
            
            full_data[:, i, :len(DYNAMIC_FEATURES)] = dyn_scaled
            full_data[:, i, len(DYNAMIC_FEATURES):] = stat_data

    X, Y = [], []
    for i in range(length - time_steps - future_steps):
        X.append(full_data[i:(i + time_steps), :, :])
        Y.append(full_data[(i + time_steps):(i + time_steps + future_steps), :, :len(DYNAMIC_FEATURES)])

    return torch.FloatTensor(np.array(X)), torch.FloatTensor(np.array(Y))
