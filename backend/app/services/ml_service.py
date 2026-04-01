import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict

try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from training.preprocess import preprocess_inference
except ImportError:
    tf = None

class MLInferenceService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.scaler_path = "backend/models/scaler.pkl"
        self.model_path = "backend/models/model.keras"
        self.time_steps = 24
        self.future_steps = 24
        self.features_count = 6
        self.is_ready = False
        
        self.load_artifacts()

    def load_artifacts(self):
        """Loads Model and Scaler at startup if they exist."""
        if tf and os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            print("Loading LSTM model and scaler...")
            self.model = load_model(self.model_path)
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            self.is_ready = True
        else:
            print("Models not found or TF not installed. Operating in fallback/API-only mode.")

    def predict(self, recent_history: pd.DataFrame) -> List[Dict[str, float]]:
        """
        Takes the last `time_steps` of hourly data and predicts the next `future_steps`.
        Returns structured list of dicts.
        """
        if not self.is_ready:
            return []

        # Predict takes exactly 24 rows
        if len(recent_history) < self.time_steps:
            raise ValueError(f"Need exactly {self.time_steps} hours of history, got {len(recent_history)}")
        
        # Take just the last 24
        recent_history = recent_history.tail(self.time_steps).copy()

        # Scale data
        scaled_input = preprocess_inference(recent_history, self.scaler_path)
        
        # Reshape for LSTM (samples, time_steps, features)
        X_input = scaled_input.reshape((1, self.time_steps, self.features_count))
        
        # Inference
        flat_predictions = self.model.predict(X_input)[0] 
        
        # Reshape back to (future_steps, features)
        y_pred_scaled = flat_predictions.reshape((self.future_steps, self.features_count))
        
        # Inverse transform
        y_pred = self.scaler.inverse_transform(y_pred_scaled)
        
        results = []
        for step in y_pred:
            results.append({
                "temperature_2m": round(float(step[0]), 2),
                "relative_humidity_2m": round(float(step[1]), 2),
                "wind_speed_10m": round(float(step[2]), 2),
                "surface_pressure": round(float(step[3]), 2),
                "precipitation": round(float(step[4]), 2),
                "weather_code": int(round(float(step[5]), 0))
            })
            
        return results

# Singleton instantiation
ml_service = MLInferenceService()
