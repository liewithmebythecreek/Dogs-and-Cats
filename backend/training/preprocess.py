import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pickle

def preprocess_data(df: pd.DataFrame, time_steps: int = 24, future_steps: int = 24, scaler_path: str = None) -> tuple:
    """
    Cleans the dataframe (fills NaNs), scales it using MinMaxScaler,
    and converts it into sequences for LSTM training.
    
    time_steps: The number of historical hours to use as input (X)
    future_steps: The number of future hours to predict as output (Y)
    scaler_path: Set this parameter if you just want to scale data using a pre-saved scaler
    """
    # Defensive missing value handling
    df = df.fillna(method='ffill').fillna(method='bfill')
    features = [
        'temperature_2m', 'relative_humidity_2m', 
        'wind_speed_10m', 'surface_pressure', 
        'precipitation', 'weather_code'
    ]
    df = df[features]
    
    # Scale Data
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)
    
    if scaler_path:
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
            print(f"Scaler saved to {scaler_path}")
            
    # Create Sequences
    X, Y = [], []
    # len(scaled_data) - time_steps - future_steps + 1
    for i in range(len(scaled_data) - time_steps - future_steps):
        # The past 'time_steps' data points
        a = scaled_data[i:(i + time_steps), :]
        X.append(a)
        
        # The future 'future_steps' data points
        b = scaled_data[(i + time_steps):(i + time_steps + future_steps), :]
        Y.append(b)

    return np.array(X), np.array(Y)

def preprocess_inference(df: pd.DataFrame, scaler_path: str) -> np.array:
    """
    For Inference/Prediction. Uses pre-saved scaler.
    Expects df with exact features in `preprocess_data`.
    """
    df = df.fillna(method='ffill').fillna(method='bfill')
    features = [
        'temperature_2m', 'relative_humidity_2m', 
        'wind_speed_10m', 'surface_pressure', 
        'precipitation', 'weather_code'
    ]
    # Ensure columns match
    df = df[features]
    
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
        
    scaled_data = scaler.transform(df)
    return scaled_data # shape (time_steps, features)

if __name__ == "__main__":
    # Test Block
    pass
