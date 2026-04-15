import datetime
import traceback
from fastapi import APIRouter, HTTPException
from app.services.weather_api import fetch_all_live_data, fetch_current_conditions
from app.services.ml_service import ml_service

router = APIRouter()


# ── Health ─────────────────────────────────────────────────────────────────────
@router.get("/health")
async def health_check():
    return {
        "status": "up",
        "ml_model_loaded": ml_service.is_ready,
    }


# ── Current conditions for all 7 nodes ────────────────────────────────────────
@router.get("/current")
async def get_current():
    """
    Returns the latest live observation for every Punjab graph node.
    """
    try:
        data = await fetch_current_conditions()
        return {"nodes": data}
    except Exception as exc:
        print("[api /current] ERROR fetching current conditions:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ── 48-hour Graph-LSTM forecast ────────────────────────────────────────────────
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
    # ── Step 1: Fetch live feature streams for all 7 nodes concurrently ───────
    try:
        city_dfs = await fetch_all_live_data()
    except Exception as exc:
        print("[api /forecast] ERROR fetching live data from Open-Meteo:")
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch live weather data: {exc}"
        )

    # ── Step 2: Validate all 7 nodes returned data ────────────────────────────
    from app.services.ml_service import CITY_NAMES
    missing_nodes = [c for c in CITY_NAMES if c not in city_dfs]
    if missing_nodes:
        msg = f"Open-Meteo returned no data for nodes: {missing_nodes}"
        print(f"[api /forecast] DATA VALIDATION FAILED – {msg}")
        raise HTTPException(status_code=502, detail=msg)

    # ── Step 3: Build current-conditions snapshot (latest row per node) ───────
    try:
        current = {}
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
    except Exception as exc:
        print("[api /forecast] ERROR building current-conditions snapshot:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse current conditions: {exc}"
        )

    # ── Step 4: Run STGNN inference (or return empty if model not loaded) ─────
    forecast = {}
    if ml_service.is_ready:
        try:
            forecast = ml_service.predict(city_dfs)
        except ValueError as exc:
            # Data-shape / validation error from ml_service — log but don't crash
            print(f"[api /forecast] ML validation error (returning empty forecast): {exc}")
            forecast = {}
        except Exception as exc:
            print("[api /forecast] ERROR during STGNN inference:")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Model inference failed: {exc}"
            )
    else:
        print("[api /forecast] Model not ready – skipping inference, returning API-only response.")

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
