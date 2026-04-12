import datetime
from fastapi import APIRouter, HTTPException
from app.services.weather_api import fetch_all_live_data, fetch_current_conditions
from app.services.ml_service import ml_service

router = APIRouter()

# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health")
async def health_check():
    return {
        "status": "up",
        "ml_model_loaded": ml_service.is_ready,
    }


# ── Current conditions for all 7 nodes ───────────────────────────────────────
@router.get("/current")
async def get_current():
    """
    Returns the latest live observation for every Punjab graph node.
    """
    try:
        data = await fetch_current_conditions()
        return {"nodes": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 48-hour Graph-LSTM forecast ───────────────────────────────────────────────
@router.get("/forecast")
async def get_forecast():
    """
    Fetches live 48-hour history for all 7 Punjab nodes, runs the
    Spatio-Temporal Graph-LSTM, and returns a structured 48-hour prediction.

    Response shape:
    {
      "metadata": { "start_time": "...", "resolution": "1h", "horizon": "48h",
                    "nodes": [...city names...] },
      "current":  { <city>: { temperature_2m, ... }, ... },
      "forecast": { <city>: [ { hour, temperature_2m, ... }, ... ], ... }
    }
    """
    try:
        # 1. Fetch live feature streams for all 7 nodes concurrently
        city_dfs = await fetch_all_live_data()

        # 2. Build current-conditions snapshot (latest row per node)
        current = {city: {} for city in city_dfs}
        for city, df in city_dfs.items():
            last = df.iloc[-1]
            current[city] = {
                "temperature_2m":       round(float(last["temperature_2m"]), 2),
                "relative_humidity_2m": round(float(last["relative_humidity_2m"]), 2),
                "wind_speed_10m":       round(float(last["wind_speed_10m"]), 2),
                "surface_pressure":     round(float(last["surface_pressure"]), 2),
                "precipitation":        round(float(last["precipitation"]), 2),
                "weather_code":         int(last["weather_code"]),
            }

        # 3. Run STGNN inference (or return empty if model not loaded)
        forecast = ml_service.predict(city_dfs) if ml_service.is_ready else {}

        start_iso = datetime.datetime.utcnow().replace(
            minute=0, second=0, microsecond=0
        ).isoformat() + "Z"

        return {
            "metadata": {
                "start_time": start_iso,
                "resolution": "1h",
                "horizon":    "48h",
                "nodes":      list(city_dfs.keys()),
            },
            "current":  current,
            "forecast": forecast,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
