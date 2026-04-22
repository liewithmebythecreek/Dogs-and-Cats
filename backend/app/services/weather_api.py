import httpx
import numpy as np
import pandas as pd
from typing import Dict, Any
import asyncio
import sys
import os

# ── Shared constants (single source of truth) ─────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
try:
    from shared_config import CITIES, CITY_NAMES, DYNAMIC_FEATURES, FORECAST_URL
except ImportError:
    from backend.shared_config import CITIES, CITY_NAMES, DYNAMIC_FEATURES, FORECAST_URL

HOURLY_VARS = DYNAMIC_FEATURES   # alias — Open-Meteo API variable names
HISTORY_URL = FORECAST_URL
CURRENT_URL = FORECAST_URL
LOCAL_TIMEZONE = "Asia/Kolkata"


async def _fetch_one_city_history(client: httpx.AsyncClient, city: str) -> pd.DataFrame:
    """Fetch 48 hours of history (past_days=2 + today) for a single node."""
    info   = CITIES[city]
    params = {
        "latitude":  info["lat"],
        "longitude": info["lon"],
        "past_hours": 48,
        "forecast_hours": 1,
        "hourly":    HOURLY_VARS,
    }
    res  = await client.get(HISTORY_URL, params=params, timeout=15)
    res.raise_for_status()
    raw  = res.json()["hourly"]

    times = pd.to_datetime(raw["time"], utc=True).tz_convert(LOCAL_TIMEZONE)
    df    = pd.DataFrame({feat: raw[feat] for feat in HOURLY_VARS}, index=times)
    df    = df.ffill().bfill()

    hours        = df.index.hour.to_numpy()
    df["sin_hour"]  = np.sin(2 * np.pi * hours / 24)
    df["cos_hour"]  = np.cos(2 * np.pi * hours / 24)
    df["elevation"] = info["elevation"]
    df["lat"]       = info["lat"]
    df["lon"]       = info["lon"]

    return df


async def fetch_all_live_data() -> Dict[str, pd.DataFrame]:
    """Concurrently fetch live 48-hour history for all 7 graph nodes."""
    async with httpx.AsyncClient() as client:
        tasks = {city: _fetch_one_city_history(client, city) for city in CITY_NAMES}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    city_data = {}
    for city, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            raise RuntimeError(f"Failed to fetch data for {city}: {result}")
        city_data[city] = result

    return city_data


async def _fetch_one_city_om_forecast(client: httpx.AsyncClient, city: str) -> list:
    """
    Fetch Open-Meteo's own 48-hour future forecast for a single city.
    Returns a list of 48 dicts matching the STGNN output schema:
      [{ hour, temperature_2m, relative_humidity_2m, wind_speed_10m,
         surface_pressure, precipitation, weather_code }, ...]
    """
    info   = CITIES[city]
    params = {
        "latitude":       info["lat"],
        "longitude":      info["lon"],
        "forecast_hours": 48,
        "hourly":         HOURLY_VARS,
        "wind_speed_unit": "kmh",
    }
    res = await client.get(FORECAST_URL, params=params, timeout=15)
    res.raise_for_status()
    raw = res.json()["hourly"]

    steps = []
    for h in range(min(48, len(raw["time"]))):
        steps.append({
            "hour":                 h + 1,
            "temperature_2m":       round(float(raw["temperature_2m"][h]       or 0), 2),
            "relative_humidity_2m": round(float(raw["relative_humidity_2m"][h] or 0), 2),
            "wind_speed_10m":       round(float(raw["wind_speed_10m"][h]       or 0), 2),
            "surface_pressure":     round(float(raw["surface_pressure"][h]     or 0), 2),
            "precipitation":        round(float(raw["precipitation"][h]        or 0), 2),
            "weather_code":         int(raw["weather_code"][h] or 0),
        })
    return steps


async def fetch_all_openmeteo_forecast() -> Dict[str, list]:
    """
    Fetch Open-Meteo's native 48-hour forecast for all 7 cities concurrently.
    Returns { city: [48 hourly dicts] } — same shape as STGNN output.
    """
    async with httpx.AsyncClient() as client:
        tasks = {city: _fetch_one_city_om_forecast(client, city) for city in CITY_NAMES}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    city_forecast = {}
    for city, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            print(f"[weather_api] OM forecast failed for {city}: {result}")
            city_forecast[city] = []
        else:
            city_forecast[city] = result

    return city_forecast


async def fetch_current_conditions() -> Dict[str, Any]:
    """Fetch the current (latest) observation for every node."""
    async with httpx.AsyncClient() as client:
        tasks = []
        for city, info in CITIES.items():
            params = {
                "latitude":  info["lat"],
                "longitude": info["lon"],
                "current":   HOURLY_VARS,
            }
            tasks.append(client.get(CURRENT_URL, params=params, timeout=10))
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    current = {}
    for city, resp in zip(CITY_NAMES, responses):
        if isinstance(resp, Exception):
            current[city] = None
            continue
        resp.raise_for_status()
        current[city] = resp.json().get("current", {})

    return current
