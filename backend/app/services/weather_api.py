import httpx
import numpy as np
import pandas as pd
from typing import Dict, Any
import asyncio

# ── City graph ────────────────────────────────────────────────────────────────
CITIES = {
    "Ropar":      {"lat": 30.9750, "lon": 76.5273, "elevation": 260},
    "Chandigarh": {"lat": 30.7333, "lon": 76.7794, "elevation": 321},
    "Ludhiana":   {"lat": 30.9010, "lon": 75.8573, "elevation": 242},
    "Patiala":    {"lat": 30.3398, "lon": 76.3869, "elevation": 250},
    "Jalandhar":  {"lat": 31.3260, "lon": 75.5762, "elevation": 228},
    "Ambala":     {"lat": 30.3782, "lon": 76.7767, "elevation": 264},
    "Shimla":     {"lat": 31.1048, "lon": 77.1734, "elevation": 2276},
}
CITY_NAMES     = list(CITIES.keys())
HOURLY_VARS    = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
                  "surface_pressure", "precipitation", "weather_code"]
HISTORY_URL    = "https://api.open-meteo.com/v1/forecast"
CURRENT_URL    = "https://api.open-meteo.com/v1/forecast"


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

    times = pd.to_datetime(raw["time"])
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
