import httpx
from typing import Dict, Any

async def fetch_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches the current weather for a specific lat/lon.
    """
    url = f"https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "surface_pressure", "precipitation", "weather_code"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("current", {})

async def fetch_forecast_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches hourly forecast for the next 24 hours (and optionally daily).
    """
    url = f"https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "surface_pressure", "precipitation_probability", "weather_code"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto",
        "forecast_days": 7
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

async def search_city(query: str) -> Dict[str, Any]:
    """
    Geocoding API to find city lat/lon.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query,
        "count": 5,
        "language": "en",
        "format": "json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
