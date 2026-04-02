import os
import datetime
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

from .data_collector import fetch_historical_data
from .preprocess import preprocess_data

# ── Hyper-parameters ──────────────────────────────────────────────────────────
TIME_STEPS    = 24
FUTURE_STEPS  = 24
FEATURES      = 6   # temp, humidity, wind, pressure, precip, weather_code

# First-run (cold start): train on a larger historical window
COLD_START_YEARS   = 2
COLD_START_EPOCHS  = 50
COLD_START_LR      = 1e-3

# Fine-tuning (daily update): only the last N days of fresh data
FINETUNE_DAYS      = 30   # fetch enough rows to build meaningful sequences
FINETUNE_EPOCHS    = 10
FINETUNE_LR        = 1e-4  # lower LR to preserve learned weights


def _build_model() -> tf.keras.Model:
    """Builds and compiles a fresh LSTM model (cold-start only)."""
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(TIME_STEPS, FEATURES)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dense(FUTURE_STEPS * FEATURES)
    ])
    model.compile(optimizer=Adam(COLD_START_LR), loss='mse',
                  metrics=['mae', 'RootMeanSquaredError'])
    return model


def train_and_evaluate(lat: float = 52.52, lon: float = 13.41):
    """
    Fine-tuning pipeline.

    • First run  – no model.keras exists yet:
        fetches 2 years of history, trains from scratch, saves model + scaler.

    • Subsequent runs (daily GitHub Actions trigger):
        loads existing model, fetches the last ~30 days of data,
        continues training with a reduced learning rate and fewer epochs.
        The scaler is NEVER re-fitted so feature scaling stays consistent.
    """
    os.makedirs('backend/models', exist_ok=True)
    model_path  = 'backend/models/model.keras'
    scaler_path = 'backend/models/scaler.pkl'

    end   = datetime.date.today() - datetime.timedelta(days=3)  # API lag

    # ── Decide: cold start vs fine-tune ──────────────────────────────────────
    is_cold_start = not os.path.exists(model_path)

    if is_cold_start:
        print("=== COLD START: no existing model found – training from scratch ===")
        start  = end - datetime.timedelta(days=365 * COLD_START_YEARS)
        epochs = COLD_START_EPOCHS
        lr     = COLD_START_LR
    else:
        print("=== FINE-TUNE: existing model found – continuing from saved weights ===")
        start  = end - datetime.timedelta(days=FINETUNE_DAYS)
        epochs = FINETUNE_EPOCHS
        lr     = FINETUNE_LR

    # ── Fetch data ────────────────────────────────────────────────────────────
    print(f"Fetching data  {start}  →  {end}  (lat={lat}, lon={lon})")
    df = fetch_historical_data(lat, lon, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    print(f"Fetched {len(df)} rows")

    # ── Preprocess ────────────────────────────────────────────────────────────
    # preprocess_data will LOAD the scaler if it exists, otherwise FIT a new one.
    print('Preprocessing...')
    X, Y = preprocess_data(df, time_steps=TIME_STEPS,
                           future_steps=FUTURE_STEPS, scaler_path=scaler_path)
    print(f"  X: {X.shape}  |  Y: {Y.shape}")

    # ── Chronological split (no shuffle – time series!) ───────────────────────
    split   = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    Y_train, Y_val = Y[:split], Y[split:]

    Y_train_flat = Y_train.reshape(Y_train.shape[0], FUTURE_STEPS * FEATURES)
    Y_val_flat   = Y_val.reshape(Y_val.shape[0],   FUTURE_STEPS * FEATURES)

    print(f"  Train: {X_train.shape}  |  Val: {X_val.shape}")

    # ── Load or build model ───────────────────────────────────────────────────
    if is_cold_start:
        model = _build_model()
        model.summary()
    else:
        model = load_model(model_path)
        # Re-compile with a lower learning rate for fine-tuning
        model.compile(optimizer=Adam(lr), loss='mse',
                      metrics=['mae', 'RootMeanSquaredError'])
        print(f"  Loaded model from {model_path}  (fine-tune LR={lr})")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=3 if not is_cold_start else 7,
        restore_best_weights=True
    )
    checkpoint = ModelCheckpoint(
        model_path,
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    print(f'Training  ({epochs} max epochs, LR={lr}) ...')
    model.fit(
        X_train, Y_train_flat,
        epochs=epochs,
        batch_size=32,
        validation_data=(X_val, Y_val_flat),
        callbacks=[early_stop, checkpoint],
        verbose=1
    )

    # ── Evaluate ─────────────────────────────────────────────────────────────
    loss, mae, rmse = model.evaluate(X_val, Y_val_flat, verbose=0)
    mode = 'Cold-start' if is_cold_start else 'Fine-tune'
    print(f'--- {mode} evaluation ---')
    print(f'  Loss : {loss:.6f}')
    print(f'  MAE  : {mae:.6f}')
    print(f'  RMSE : {rmse:.6f}')
    print(f'Model saved to {model_path}')
    print(f'Scaler at     {scaler_path}')


if __name__ == '__main__':
    train_and_evaluate()
