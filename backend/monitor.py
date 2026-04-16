"""
backend/monitor.py
Drift Detection — compares the model's stored predictions against actual
Open-Meteo observations for the past 7 days. Exits with code 1 if MAE
exceeds the configured threshold (default: 2.0°C for temperature).

Usage:
    python -m backend.monitor
    python -m backend.monitor --threshold 1.5 --days 7

Exit codes:
    0  — no drift detected (MAE within threshold)
    1  — DRIFT_DETECTED (MAE > threshold, trigger retraining)
    2  — log file missing or insufficient data (skip retraining this cycle)
"""

import os
import sys
import json
import argparse
import datetime
import asyncio
import numpy as np

# ── Import the live API fetcher (shared with the inference server) ─────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from app.services.weather_api import fetch_all_live_data, CITY_NAMES, HOURLY_VARS

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_THRESHOLD_C = 2.0   # MAE >2°C → trigger fine-tuning
DEFAULT_DRIFT_DAYS  = 7
FORECAST_LOG_PATH   = 'backend/data/forecast_log.jsonl'  # written by the API server


# ── Actual weather fetcher ────────────────────────────────────────────────────

async def fetch_actuals(days: int) -> dict:
    """
    Returns {city: [actual_temp_hour0, actual_temp_hour1, ...]} for the last
    `days * 24` hours across all 7 cities.
    Uses the same fetch_all_live_data() pipeline as the inference server,
    ensuring normalisation/feature logic is identical (no Training-Serving Skew).
    """
    import httpx
    import pandas as pd

    hours_back = days * 24
    actuals = {}

    async with httpx.AsyncClient() as client:
        for city in CITY_NAMES:
            from app.services.weather_api import CITIES, HISTORY_URL
            params = {
                "latitude":      CITIES[city]["lat"],
                "longitude":     CITIES[city]["lon"],
                "past_hours":    hours_back,
                "forecast_hours": 1,
                "hourly":        HOURLY_VARS,
            }
            resp = await client.get(HISTORY_URL, params=params, timeout=20)
            resp.raise_for_status()
            raw = resp.json()["hourly"]
            actuals[city] = raw["temperature_2m"]   # list of floats

    return actuals


# ── Forecast log reader ───────────────────────────────────────────────────────

def load_forecast_log(days: int) -> dict:
    """
    Reads backend/data/forecast_log.jsonl (one JSON object per line).
    Each line written by the API server looks like:
      {"ts": "2026-04-10T00:00:00Z", "city": "Ropar", "hour": 1, "temperature_2m": 28.4}

    Returns {city: [pred_temp, ...]} ordered by timestamp ascending,
    limited to the last `days` worth of entries.
    """
    if not os.path.exists(FORECAST_LOG_PATH):
        print(f"[monitor] Forecast log not found at {FORECAST_LOG_PATH}.", file=sys.stderr)
        return {}

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    preds  = {city: [] for city in CITY_NAMES}

    with open(FORECAST_LOG_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts    = datetime.datetime.fromisoformat(entry["ts"].replace("Z", ""))
                if ts >= cutoff and entry["city"] in preds:
                    preds[entry["city"]].append(entry["temperature_2m"])
            except (json.JSONDecodeError, KeyError):
                continue

    return preds


# ── MAE calculation ───────────────────────────────────────────────────────────

def compute_mae(actuals: dict, predictions: dict) -> dict:
    """
    Returns {city: mae_celsius}. Pairs entries by index (oldest first).
    Cities with insufficient data are skipped.
    """
    mae_per_city = {}
    for city in CITY_NAMES:
        act  = np.array(actuals.get(city, []),     dtype=float)
        pred = np.array(predictions.get(city, []), dtype=float)

        if len(act) == 0 or len(pred) == 0:
            print(f"[monitor] {city}: no data to compare — skipping.")
            continue

        n = min(len(act), len(pred))
        mae_per_city[city] = float(np.mean(np.abs(act[-n:] - pred[-n:])))

    return mae_per_city


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(threshold: float, days: int):
    print(f"[monitor] Drift detection — last {days} days | threshold={threshold}°C")

    # 1. Fetch actual observations from Open-Meteo
    print("[monitor] Fetching actuals from Open-Meteo …")
    try:
        actuals = await fetch_actuals(days)
    except Exception as e:
        print(f"[monitor] Failed to fetch actuals: {e}", file=sys.stderr)
        sys.exit(2)

    # 2. Load stored model predictions
    print("[monitor] Loading forecast log …")
    predictions = load_forecast_log(days)

    if not any(len(v) > 0 for v in predictions.values()):
        print("[monitor] No forecast log entries found — cannot detect drift.", file=sys.stderr)
        print("[monitor] Hint: ensure the API server writes to backend/data/forecast_log.jsonl")
        sys.exit(2)

    # 3. Compute MAE per city
    mae = compute_mae(actuals, predictions)
    if not mae:
        print("[monitor] Insufficient data for MAE calculation.", file=sys.stderr)
        sys.exit(2)

    # 4. Report
    print("\n── Drift Report ────────────────────────────────────────────────────")
    print(f"  {'City':<14} {'MAE (°C)':>10}  {'Status'}")
    print("  " + "─" * 42)
    max_mae = 0.0
    for city, err in sorted(mae.items(), key=lambda x: -x[1]):
        status  = "⚠ DRIFT" if err > threshold else "ok"
        max_mae = max(max_mae, err)
        print(f"  {city:<14} {err:>10.2f}°C  {status}")

    overall_mae = float(np.mean(list(mae.values())))
    print("  " + "─" * 42)
    print(f"  {'OVERALL':<14} {overall_mae:>10.2f}°C  "
          f"{'⚠ DRIFT DETECTED' if overall_mae > threshold else 'ok'}")
    print("────────────────────────────────────────────────────────────────────\n")

    # 5. Gate
    if overall_mae > threshold:
        print(f"DRIFT_DETECTED  (MAE={overall_mae:.2f}°C > threshold={threshold}°C)")
        sys.exit(1)
    else:
        print(f"NO_DRIFT  (MAE={overall_mae:.2f}°C ≤ threshold={threshold}°C)")
        sys.exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='STGNN Drift Detector')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD_C,
                        help='MAE threshold in °C above which drift is declared (default: 2.0)')
    parser.add_argument('--days',      type=int,   default=DEFAULT_DRIFT_DAYS,
                        help='Number of past days to evaluate (default: 7)')
    args = parser.parse_args()
    asyncio.run(main(args.threshold, args.days))
