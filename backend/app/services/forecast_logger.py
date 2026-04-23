"""
backend/app/services/forecast_logger.py
Appends each STGNN prediction to a JSONL file so drift checks can compare
predictions against actual observations.
"""

import datetime
import json
import os
from typing import Any, Dict, List

from app.services.drift_utils import FORECAST_LOG_PATH


MAX_LOG_BYTES = 50 * 1024 * 1024  # 50 MB, rotate beyond this size


def log_forecast(forecast: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Append one batch of STGNN forecast results to the JSONL log.
    Called from api.py after a successful /forecast response.
    """
    if not forecast:
        return

    os.makedirs(os.path.dirname(FORECAST_LOG_PATH), exist_ok=True)

    if os.path.exists(FORECAST_LOG_PATH) and os.path.getsize(FORECAST_LOG_PATH) > MAX_LOG_BYTES:
        rotated = FORECAST_LOG_PATH + ".old"
        os.replace(FORECAST_LOG_PATH, rotated)
        print(f"[forecast_logger] Rotated log to {rotated}")

    base_ts = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    with open(FORECAST_LOG_PATH, "a", encoding="utf-8") as handle:
        for city, steps in forecast.items():
            for step in steps:
                entry = {
                    "ts": (base_ts + datetime.timedelta(hours=step["hour"] - 1)).isoformat() + "Z",
                    "city": city,
                    **{k: v for k, v in step.items() if k != "hour"},
                }
                handle.write(json.dumps(entry) + "\n")

