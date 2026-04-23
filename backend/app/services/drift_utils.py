"""
Utilities for model-drift evaluation shared by:
  - backend/monitor.py (CLI drift gate)
  - Prometheus background drift checks in the FastAPI app
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
from pathlib import Path
from typing import Dict, List

import httpx
import numpy as np

try:
    from shared_config import CITIES, CITY_NAMES, FORECAST_URL
except ImportError:
    from backend.shared_config import CITIES, CITY_NAMES, FORECAST_URL


DEFAULT_THRESHOLD_C = 2.0
DEFAULT_DRIFT_DAYS = 7
DEFAULT_FORECAST_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "forecast_log.jsonl"
FORECAST_LOG_PATH = os.getenv("FORECAST_LOG_PATH", str(DEFAULT_FORECAST_LOG_PATH))


async def _fetch_city_actuals(client: httpx.AsyncClient, city: str, hours_back: int) -> List[float]:
    params = {
        "latitude": CITIES[city]["lat"],
        "longitude": CITIES[city]["lon"],
        "past_hours": hours_back,
        "forecast_hours": 1,
        "hourly": "temperature_2m",
    }
    response = await client.get(FORECAST_URL, params=params, timeout=20)
    response.raise_for_status()
    raw = response.json().get("hourly", {})
    return [float(v) for v in raw.get("temperature_2m", []) if v is not None]


async def fetch_actuals(days: int) -> Dict[str, List[float]]:
    """
    Returns {city: [actual_temp, ...]} for the last `days * 24` hours.
    """
    hours_back = max(days, 1) * 24
    async with httpx.AsyncClient() as client:
        tasks = {
            city: _fetch_city_actuals(client, city, hours_back)
            for city in CITY_NAMES
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    actuals: Dict[str, List[float]] = {}
    for city, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            raise RuntimeError(f"Failed to fetch actuals for {city}: {result}") from result
        actuals[city] = result
    return actuals


def _parse_timestamp_utc(ts: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def load_forecast_log(days: int, path: str = FORECAST_LOG_PATH) -> Dict[str, List[float]]:
    """
    Reads forecast log and returns {city: [pred_temp, ...]} for entries newer than cutoff.
    """
    predictions = {city: [] for city in CITY_NAMES}
    log_path = Path(path)
    if not log_path.exists():
        return predictions

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max(days, 1))

    with log_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                city = entry.get("city")
                if city not in predictions:
                    continue

                entry_ts = _parse_timestamp_utc(str(entry.get("ts", "")))
                if entry_ts < cutoff:
                    continue

                value = entry.get("temperature_2m")
                if value is None:
                    continue
                predictions[city].append(float(value))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

    return predictions


def compute_mae(actuals: Dict[str, List[float]], predictions: Dict[str, List[float]]) -> Dict[str, float]:
    """
    Returns {city: mae_celsius}. Pairs values by index from the tail of each list.
    """
    mae_per_city: Dict[str, float] = {}
    for city in CITY_NAMES:
        actual = np.asarray(actuals.get(city, []), dtype=float)
        pred = np.asarray(predictions.get(city, []), dtype=float)
        if actual.size == 0 or pred.size == 0:
            continue

        paired_size = min(actual.size, pred.size)
        mae = np.mean(np.abs(actual[-paired_size:] - pred[-paired_size:]))
        mae_per_city[city] = float(mae)
    return mae_per_city

