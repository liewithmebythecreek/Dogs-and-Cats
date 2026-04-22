import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
from retry_requests import retry
import datetime
from geopy.distance import geodesic
import sys
import os

# ── Shared constants ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared_config import (
    CITIES, CITY_NAMES, NUM_NODES,
    DYNAMIC_FEATURES, GRAPH_THRESHOLD_KM, ARCHIVE_URL,
)


cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
LOCAL_TIMEZONE = "Asia/Kolkata"


def build_graph_edges(threshold_km=GRAPH_THRESHOLD_KM):
    edges = []
    edge_attr = []
    for i, city_i in enumerate(CITY_NAMES):
        for j, city_j in enumerate(CITY_NAMES):
            if i != j:
                loc_i = (CITIES[city_i]["lat"], CITIES[city_i]["lon"])
                loc_j = (CITIES[city_j]["lat"], CITIES[city_j]["lon"])
                dist = geodesic(loc_i, loc_j).km
                if dist <= threshold_km:
                    edges.append([i, j])
                    edge_attr.append([dist])
    return edges, edge_attr

def fetch_historical_data(start_date: str, end_date: str) -> dict:
    url = ARCHIVE_URL
    
    lats = [CITIES[name]["lat"] for name in CITY_NAMES]
    lons = [CITIES[name]["lon"] for name in CITY_NAMES]

    params = {
        "latitude":  lats,
        "longitude": lons,
        "start_date": start_date,
        "end_date":   end_date,
        "hourly":     DYNAMIC_FEATURES,
    }
    
    responses = openmeteo.weather_api(url, params=params)
    
    city_data = {}
    for i, response in enumerate(responses):
        city = CITY_NAMES[i]
        hourly = response.Hourly()
        
        temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
        surface_pressure = hourly.Variables(3).ValuesAsNumpy()
        precipitation = hourly.Variables(4).ValuesAsNumpy()
        weather_code = hourly.Variables(5).ValuesAsNumpy()
        
        dates_utc = pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )

        dates = dates_utc.tz_convert(LOCAL_TIMEZONE)
        hours = dates.hour.to_numpy()
        sin_hour = np.sin(2 * np.pi * hours / 24)
        cos_hour = np.cos(2 * np.pi * hours / 24)
        
        df = pd.DataFrame({
            "date": dates,
            "temperature_2m": temperature_2m,
            "relative_humidity_2m": relative_humidity_2m,
            "wind_speed_10m": wind_speed_10m,
            "surface_pressure": surface_pressure,
            "precipitation": precipitation,
            "weather_code": weather_code,
            "sin_hour": sin_hour,
            "cos_hour": cos_hour,
            "elevation": CITIES[city]["elevation"],
            "lat": CITIES[city]["lat"],
            "lon": CITIES[city]["lon"]
        })
        df.set_index("date", inplace=True)
        city_data[city] = df
        
    return city_data

if __name__ == "__main__":
    end = datetime.date.today() - datetime.timedelta(days=2)
    start = end - datetime.timedelta(days=3)
    data = fetch_historical_data(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print(f"Fetched data for {len(data)} cities")
    for city, df in data.items():
        print(f"{city}: {df.shape}")
