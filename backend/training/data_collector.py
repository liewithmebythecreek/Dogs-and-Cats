import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import datetime
import os

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def fetch_historical_data(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical weather data from Open-Meteo API.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "surface_pressure", "precipitation", "weather_code"]
    }
    
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    
    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    
    temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    surface_pressure = hourly.Variables(3).ValuesAsNumpy()
    precipitation = hourly.Variables(4).ValuesAsNumpy()
    weather_code = hourly.Variables(5).ValuesAsNumpy()
    
    hourly_data = {"date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )}
    hourly_data["temperature_2m"] = temperature_2m
    hourly_data["relative_humidity_2m"] = relative_humidity_2m
    hourly_data["wind_speed_10m"] = wind_speed_10m
    hourly_data["surface_pressure"] = surface_pressure
    hourly_data["precipitation"] = precipitation
    hourly_data["weather_code"] = weather_code

    df = pd.DataFrame(data=hourly_data)
    df.set_index("date", inplace=True)
    return df

if __name__ == "__main__":
    # Test fetch
    end = datetime.date.today() - datetime.timedelta(days=2) # History API might lag by a couple of days
    start = end - datetime.timedelta(days=365) # Get 1 year of data
    df = fetch_historical_data(52.52, 13.41, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")) # Default to Berlin
    print(df.head())
    print(f"Shape: {df.shape}")
