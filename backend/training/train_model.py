import os
import datetime
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.model_selection import train_test_split

from .data_collector import fetch_historical_data
from .preprocess import preprocess_data

def train_and_evaluate(lat: float = 52.52, lon: float = 13.41, years: int = 2):
    """
    Combines fetching, preprocessing, and training into a single pipeline.
    """
    print(f"--- Fething History Data for lat={lat}, lon={lon} ---")
    end = datetime.date.today() - datetime.timedelta(days=3)
    start = end - datetime.timedelta(days=365 * years)
    
    df = fetch_historical_data(lat, lon, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print(f"Data Fetched. Shape: {df.shape}")
    
    os.makedirs('backend/models', exist_ok=True)
    scaler_path = "backend/models/scaler.pkl"
    model_path = "backend/models/model.keras" # .h5 is legacy, using .keras
    
    time_steps = 24
    future_steps = 24
    features_count = 6 # temp, humidity, wind, pressure, precip, weather code
    
    print("--- Preprocessing Data ---")
    X, Y = preprocess_data(df, time_steps=time_steps, future_steps=future_steps, scaler_path=scaler_path)
    
    print(f"X shape: {X.shape}") # (samples, time_steps, features)
    print(f"Y shape: {Y.shape}") # (samples, future_steps, features)
    
    # Chronological Split (No Shuffling)
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    Y_train, Y_test = Y[:split], Y[split:]
    
    print(f"Training shapes. X: {X_train.shape}, Y: {Y_train.shape}")
    print(f"Validation shapes. X: {X_test.shape}, Y: {Y_test.shape}")
    
    # Define LSTM architecture
    print("--- Building Model ---")
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(time_steps, features_count)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        # Output layer maps back to future_steps * features_count so we can reshape
        Dense(future_steps * features_count) 
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae', 'RootMeanSquaredError'])
    model.summary()
    
    # Reshape Y back to flat for Dense layer output
    Y_train_flat = Y_train.reshape((Y_train.shape[0], future_steps * features_count))
    Y_test_flat = Y_test.reshape((Y_test.shape[0], future_steps * features_count))
    
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    checkpoint = ModelCheckpoint(model_path, monitor='val_loss', save_best_only=True)
    
    print("--- Training Model ---")
    # Quick defaults, epochs set to 20 to balance GitHub workflow timeout
    history = model.fit(
        X_train, Y_train_flat, 
        epochs=15, 
        batch_size=32, 
        validation_data=(X_test, Y_test_flat), 
        callbacks=[early_stop, checkpoint],
        verbose=1
    )
    
    loss, mae, rmse = model.evaluate(X_test, Y_test_flat)
    print(f"--- Evaluation complete ---")
    print(f"MAE: {mae}")
    print(f"RMSE: {rmse}")
    
    print(f"Model and Scaler completely outputted to backend/models/")

if __name__ == "__main__":
    train_and_evaluate()
