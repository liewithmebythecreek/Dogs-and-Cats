from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.weather_api import fetch_current_weather, fetch_forecast_weather, search_city
from app.services.ml_service import ml_service
import pandas as pd
import httpx

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "up",
        "ml_model_loaded": ml_service.is_ready
    }

@router.get("/locations/search")
async def search_locations(q: str = Query(..., min_length=2)):
    try:
        results = await search_city(q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current/{lat}/{lon}")
async def get_current(lat: float, lon: float):
    try:
        data = await fetch_current_weather(lat, lon)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast/{lat}/{lon}")
async def get_forecast(lat: float, lon: float):
    """
    Returns the Open Meteo forecast and also attempts to generate 
    an ML prediction for comparison if the model is ready.
    """
    try:
        forecast_data = await fetch_forecast_weather(lat, lon)
        
        ml_predictions = []
        if ml_service.is_ready:
            # We need the last 24 hours of data for a prediction. 
            # We'll fetch real history from open-meteo just-in-time to feed the model
            url = "https://api.open-meteo.com/v1/forecast"
            hist_params = {
                "latitude": lat,
                "longitude": lon,
                "past_days": 2, 
                "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "surface_pressure", "precipitation", "weather_code"]
            }
            async with httpx.AsyncClient() as client:
                hist_res = await client.get(url, params=hist_params)
                hist_json = hist_res.json()
            
            # Extract last 24 hours before 'now'
            # Note: For production, we would cleanly slice the time array to exactly 24 hours behind 'current time'.
            # As a simplified approach, we just use the last 24 valid records available.
            df = pd.DataFrame(hist_json['hourly'])
            # Only keep the 6 features
            ml_predictions = ml_service.predict(df)
            
        forecast_data["ml_predictions"] = ml_predictions
        return forecast_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
