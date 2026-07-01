import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

LOCATIONS = {
    "Pakistan": [
        {"city": "Karachi",       "lat": 24.86,  "lon": 67.01,  "district": "Karachi"},
        {"city": "Lahore",        "lat": 31.55,  "lon": 74.35,  "district": "Lahore"},
        {"city": "Islamabad",     "lat": 33.72,  "lon": 73.04,  "district": "Islamabad"},
        {"city": "Peshawar",      "lat": 34.01,  "lon": 71.58,  "district": "Peshawar"},
        {"city": "Quetta",        "lat": 30.19,  "lon": 67.01,  "district": "Quetta"},
        {"city": "Multan",        "lat": 30.19,  "lon": 71.47,  "district": "Multan"},
        {"city": "Faisalabad",    "lat": 31.42,  "lon": 73.08,  "district": "Faisalabad"},
        {"city": "Hyderabad",     "lat": 25.37,  "lon": 68.37,  "district": "Hyderabad"},
        {"city": "Rawalpindi",    "lat": 33.60,  "lon": 73.04,  "district": "Rawalpindi"},
        {"city": "Gilgit",        "lat": 35.92,  "lon": 74.31,  "district": "Gilgit"},
        {"city": "Muzaffarabad",  "lat": 34.37,  "lon": 73.47,  "district": "Muzaffarabad"},
        {"city": "Sialkot",       "lat": 32.49,  "lon": 74.53,  "district": "Sialkot"},
    ],
    "India": [
        {"city": "New Delhi",     "lat": 28.61,  "lon": 77.21,  "district": "New Delhi"},
        {"city": "Amritsar",      "lat": 31.63,  "lon": 74.87,  "district": "Amritsar"},
        {"city": "Jaipur",        "lat": 26.92,  "lon": 75.79,  "district": "Jaipur"},
        {"city": "Srinagar",      "lat": 34.09,  "lon": 74.80,  "district": "Srinagar"},
        {"city": "Mumbai",        "lat": 19.07,  "lon": 72.88,  "district": "Mumbai"},
    ],
    "Afghanistan": [
        {"city": "Kabul",         "lat": 34.53,  "lon": 69.17,  "district": "Kabul"},
        {"city": "Kandahar",      "lat": 31.61,  "lon": 65.71,  "district": "Kandahar"},
        {"city": "Jalalabad",     "lat": 34.43,  "lon": 70.45,  "district": "Jalalabad"},
        {"city": "Herat",         "lat": 34.35,  "lon": 62.20,  "district": "Herat"},
    ],
    "Iran": [
        {"city": "Tehran",        "lat": 35.69,  "lon": 51.42,  "district": "Tehran"},
        {"city": "Mashhad",       "lat": 36.30,  "lon": 59.60,  "district": "Mashhad"},
        {"city": "Zahedan",       "lat": 29.50,  "lon": 60.86,  "district": "Zahedan"},
        {"city": "Ahvaz",         "lat": 31.32,  "lon": 48.67,  "district": "Ahvaz"},
    ],
    "China": [
        {"city": "Urumqi",        "lat": 43.82,  "lon": 87.62,  "district": "Urumqi"},
        {"city": "Kashgar",       "lat": 39.47,  "lon": 75.99,  "district": "Kashgar"},
        {"city": "Hotan",         "lat": 37.11,  "lon": 79.92,  "district": "Hotan"},
    ],
}

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "windspeed_10m_max",
    "winddirection_10m_dominant",
    "et0_fao_evapotranspiration",
    "weathercode",
]

START_DATE = "2022-01-01"
END_DATE   = "2023-12-31"


def fetch_location(loc: dict, country: str) -> pd.DataFrame | None:
    params = {
        "latitude":   loc["lat"],
        "longitude":  loc["lon"],
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "daily":      ",".join(DAILY_VARS),
        "timezone":   "auto",
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data["daily"])
        df["city"]     = loc["city"]
        df["district"] = loc["district"]
        df["country"]  = country
        df["lat"]      = loc["lat"]
        df["lon"]      = loc["lon"]
        return df
    except Exception as e:
        print(f"  Failed {loc['city']}: {e}")
        return None


def collect_all() -> pd.DataFrame:
    frames = []
    for country, locs in LOCATIONS.items():
        print(f"Collecting {country}...")
        for loc in locs:
            df = fetch_location(loc, country)
            if df is not None:
                frames.append(df)
                print(f"  OK  {loc['city']}  ({len(df)} rows)")
            time.sleep(0.4)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main():
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)
    df = collect_all()
    if df.empty:
        print("API unavailable. Falling back to synthetic data generator.")
        from src.generate_synthetic import generate_all
        df = generate_all()
    else:
        path = out_dir / "weather_raw.csv"
        df.to_csv(path, index=False)
        print(f"\nSaved {len(df)} rows to {path}")
    return df


if __name__ == "__main__":
    main()
