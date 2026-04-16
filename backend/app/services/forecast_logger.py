"""
backend/app/services/forecast_logger.py
Appends each STGNN prediction to a JSONL file so monitor.py can compare
them against actual observations during drift detection.

Format (one JSON object per line):
  {"ts": "2026-04-10T03:00:00Z", "city": "Ropar", "hour": 1,
   "temperature_2m": 28.4, "relative_humidity_2m": 48.0, ...}
"""

import os
import json
import datetime
from typing import Dict, List, Any

FORECAST_LOG_PATH = 'backend/data/forecast_log.jsonl'
MAX_LOG_BYTES     = 50 * 1024 * 1024   # 50 MB — rotate beyond this


def log_forecast(forecast: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Append one batch of STGNN forecast results to the JSONL log.
    Called from api.py after a successful /forecast response.
    """
    if not forecast:
        return

    os.makedirs(os.path.dirname(FORECAST_LOG_PATH), exist_ok=True)

    # Rotate if log is too large
    if os.path.exists(FORECAST_LOG_PATH):
        if os.path.getsize(FORECAST_LOG_PATH) > MAX_LOG_BYTES:
            rotated = FORECAST_LOG_PATH + '.old'
            os.replace(FORECAST_LOG_PATH, rotated)
            print(f"[forecast_logger] Rotated log to {rotated}")

    base_ts = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    with open(FORECAST_LOG_PATH, 'a') as f:
        for city, steps in forecast.items():
            for step in steps:
                entry = {
                    "ts":   (base_ts + datetime.timedelta(hours=step["hour"] - 1)).isoformat() + "Z",
                    "city": city,
                    **{k: v for k, v in step.items() if k != "hour"},
                }
                f.write(json.dumps(entry) + "\n")
