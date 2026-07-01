"""
Generates synthetic weather data in the exact format returned by Open-Meteo.
Used only when the real API is unavailable (e.g. no network, rate limits).
The collect_weather.py script will use real API data whenever possible and
fall back to this only if the API call fails.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42

CLIMATE_PROFILES = {
    "Karachi":      {"tmax_mu": 34, "tmax_sd": 6,  "precip_mu": 1.2, "wind_mu": 18},
    "Lahore":       {"tmax_mu": 33, "tmax_sd": 9,  "precip_mu": 1.8, "wind_mu": 12},
    "Islamabad":    {"tmax_mu": 28, "tmax_sd": 10, "precip_mu": 2.5, "wind_mu": 14},
    "Peshawar":     {"tmax_mu": 31, "tmax_sd": 10, "precip_mu": 1.5, "wind_mu": 13},
    "Quetta":       {"tmax_mu": 26, "tmax_sd": 12, "precip_mu": 0.9, "wind_mu": 16},
    "Multan":       {"tmax_mu": 35, "tmax_sd": 9,  "precip_mu": 1.1, "wind_mu": 13},
    "Faisalabad":   {"tmax_mu": 33, "tmax_sd": 9,  "precip_mu": 1.4, "wind_mu": 11},
    "Hyderabad":    {"tmax_mu": 36, "tmax_sd": 7,  "precip_mu": 1.0, "wind_mu": 22},
    "Rawalpindi":   {"tmax_mu": 29, "tmax_sd": 10, "precip_mu": 2.6, "wind_mu": 13},
    "Gilgit":       {"tmax_mu": 24, "tmax_sd": 12, "precip_mu": 1.0, "wind_mu": 15},
    "Muzaffarabad": {"tmax_mu": 26, "tmax_sd": 11, "precip_mu": 3.2, "wind_mu": 11},
    "Sialkot":      {"tmax_mu": 31, "tmax_sd": 9,  "precip_mu": 2.0, "wind_mu": 12},
    "New Delhi":    {"tmax_mu": 33, "tmax_sd": 9,  "precip_mu": 1.8, "wind_mu": 14},
    "Amritsar":     {"tmax_mu": 31, "tmax_sd": 9,  "precip_mu": 1.9, "wind_mu": 12},
    "Jaipur":       {"tmax_mu": 35, "tmax_sd": 8,  "precip_mu": 1.4, "wind_mu": 16},
    "Srinagar":     {"tmax_mu": 20, "tmax_sd": 12, "precip_mu": 2.2, "wind_mu": 10},
    "Mumbai":       {"tmax_mu": 32, "tmax_sd": 3,  "precip_mu": 4.5, "wind_mu": 20},
    "Kabul":        {"tmax_mu": 22, "tmax_sd": 14, "precip_mu": 0.8, "wind_mu": 14},
    "Kandahar":     {"tmax_mu": 28, "tmax_sd": 13, "precip_mu": 0.5, "wind_mu": 18},
    "Jalalabad":    {"tmax_mu": 27, "tmax_sd": 12, "precip_mu": 0.6, "wind_mu": 13},
    "Herat":        {"tmax_mu": 25, "tmax_sd": 14, "precip_mu": 0.6, "wind_mu": 20},
    "Tehran":       {"tmax_mu": 23, "tmax_sd": 13, "precip_mu": 0.7, "wind_mu": 15},
    "Mashhad":      {"tmax_mu": 24, "tmax_sd": 13, "precip_mu": 0.5, "wind_mu": 14},
    "Zahedan":      {"tmax_mu": 29, "tmax_sd": 12, "precip_mu": 0.3, "wind_mu": 18},
    "Ahvaz":        {"tmax_mu": 34, "tmax_sd": 11, "precip_mu": 0.6, "wind_mu": 19},
    "Urumqi":       {"tmax_mu": 14, "tmax_sd": 18, "precip_mu": 0.5, "wind_mu": 17},
    "Kashgar":      {"tmax_mu": 20, "tmax_sd": 16, "precip_mu": 0.2, "wind_mu": 15},
    "Hotan":        {"tmax_mu": 22, "tmax_sd": 16, "precip_mu": 0.1, "wind_mu": 14},
}

LOCATION_META = {
    "Karachi":      {"country": "Pakistan",     "district": "Karachi",      "lat": 24.86, "lon": 67.01},
    "Lahore":       {"country": "Pakistan",     "district": "Lahore",       "lat": 31.55, "lon": 74.35},
    "Islamabad":    {"country": "Pakistan",     "district": "Islamabad",    "lat": 33.72, "lon": 73.04},
    "Peshawar":     {"country": "Pakistan",     "district": "Peshawar",     "lat": 34.01, "lon": 71.58},
    "Quetta":       {"country": "Pakistan",     "district": "Quetta",       "lat": 30.19, "lon": 67.01},
    "Multan":       {"country": "Pakistan",     "district": "Multan",       "lat": 30.19, "lon": 71.47},
    "Faisalabad":   {"country": "Pakistan",     "district": "Faisalabad",   "lat": 31.42, "lon": 73.08},
    "Hyderabad":    {"country": "Pakistan",     "district": "Hyderabad",    "lat": 25.37, "lon": 68.37},
    "Rawalpindi":   {"country": "Pakistan",     "district": "Rawalpindi",   "lat": 33.60, "lon": 73.04},
    "Gilgit":       {"country": "Pakistan",     "district": "Gilgit",       "lat": 35.92, "lon": 74.31},
    "Muzaffarabad": {"country": "Pakistan",     "district": "Muzaffarabad", "lat": 34.37, "lon": 73.47},
    "Sialkot":      {"country": "Pakistan",     "district": "Sialkot",      "lat": 32.49, "lon": 74.53},
    "New Delhi":    {"country": "India",        "district": "New Delhi",    "lat": 28.61, "lon": 77.21},
    "Amritsar":     {"country": "India",        "district": "Amritsar",     "lat": 31.63, "lon": 74.87},
    "Jaipur":       {"country": "India",        "district": "Jaipur",       "lat": 26.92, "lon": 75.79},
    "Srinagar":     {"country": "India",        "district": "Srinagar",     "lat": 34.09, "lon": 74.80},
    "Mumbai":       {"country": "India",        "district": "Mumbai",       "lat": 19.07, "lon": 72.88},
    "Kabul":        {"country": "Afghanistan",  "district": "Kabul",        "lat": 34.53, "lon": 69.17},
    "Kandahar":     {"country": "Afghanistan",  "district": "Kandahar",     "lat": 31.61, "lon": 65.71},
    "Jalalabad":    {"country": "Afghanistan",  "district": "Jalalabad",    "lat": 34.43, "lon": 70.45},
    "Herat":        {"country": "Afghanistan",  "district": "Herat",        "lat": 34.35, "lon": 62.20},
    "Tehran":       {"country": "Iran",         "district": "Tehran",       "lat": 35.69, "lon": 51.42},
    "Mashhad":      {"country": "Iran",         "district": "Mashhad",      "lat": 36.30, "lon": 59.60},
    "Zahedan":      {"country": "Iran",         "district": "Zahedan",      "lat": 29.50, "lon": 60.86},
    "Ahvaz":        {"country": "Iran",         "district": "Ahvaz",        "lat": 31.32, "lon": 48.67},
    "Urumqi":       {"country": "China",        "district": "Urumqi",       "lat": 43.82, "lon": 87.62},
    "Kashgar":      {"country": "China",        "district": "Kashgar",      "lat": 39.47, "lon": 75.99},
    "Hotan":        {"country": "China",        "district": "Hotan",        "lat": 37.11, "lon": 79.92},
}

WMO_MAP = [0, 1, 2, 3, 45, 51, 61, 63, 65, 80, 81, 82, 95]


def _season_offset(day_of_year: np.ndarray, city: str) -> np.ndarray:
    """Sinusoidal temperature seasonal cycle."""
    phase = 2 * np.pi * (day_of_year - 15) / 365
    amplitude = 14 if "Pakistan" in LOCATION_META.get(city, {}).get("country", "") else 12
    return amplitude * np.sin(phase)


def generate_city(city: str, start: str = "2022-01-01", end: str = "2023-12-31") -> pd.DataFrame:
    rng = np.random.default_rng(SEED + hash(city) % 1000)
    dates = pd.date_range(start, end, freq="D")
    n = len(dates)
    doy = dates.day_of_year.values
    prof = CLIMATE_PROFILES[city]
    meta = LOCATION_META[city]

    season = _season_offset(doy, city)
    tmax = prof["tmax_mu"] + season + rng.normal(0, prof["tmax_sd"] * 0.3, n)
    tmin = tmax - rng.uniform(8, 16, n)
    tmean = (tmax + tmin) / 2

    precip_raw = rng.exponential(prof["precip_mu"], n)
    dry_mask = rng.random(n) < 0.65
    precip = np.where(dry_mask, 0.0, precip_raw)

    monsoon_mask = (dates.month >= 7) & (dates.month <= 9)
    if meta["country"] in ("Pakistan", "India"):
        precip[monsoon_mask] *= rng.uniform(3, 8, monsoon_mask.sum())

    wind = np.abs(rng.normal(prof["wind_mu"], prof["wind_mu"] * 0.6, n))
    wind_dir = rng.uniform(0, 360, n)
    wmo = rng.choice(WMO_MAP, n)

    df = pd.DataFrame({
        "time":                         dates.strftime("%Y-%m-%d"),
        "temperature_2m_max":           np.round(tmax, 1),
        "temperature_2m_min":           np.round(tmin, 1),
        "temperature_2m_mean":          np.round(tmean, 1),
        "precipitation_sum":            np.round(np.clip(precip, 0, None), 1),
        "windspeed_10m_max":            np.round(wind, 1),
        "winddirection_10m_dominant":   np.round(wind_dir, 0),
        "et0_fao_evapotranspiration":   np.round(rng.uniform(1, 8, n), 2),
        "weathercode":                  wmo,
        "city":                         city,
        "district":                     meta["district"],
        "country":                      meta["country"],
        "lat":                          meta["lat"],
        "lon":                          meta["lon"],
    })
    return df


def generate_all(out_path: str = "data/weather_raw.csv"):
    Path("data").mkdir(exist_ok=True)
    frames = [generate_city(city) for city in LOCATION_META]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df):,} rows for {len(LOCATION_META)} cities -> {out_path}")
    return df


if __name__ == "__main__":
    generate_all()
