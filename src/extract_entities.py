import pandas as pd
import numpy as np
from pathlib import Path


WMO_CODES = {
    0:   "Clear sky",
    1:   "Mainly clear",
    2:   "Partly cloudy",
    3:   "Overcast",
    45:  "Fog",
    48:  "Rime fog",
    51:  "Light drizzle",
    53:  "Moderate drizzle",
    55:  "Dense drizzle",
    61:  "Slight rain",
    63:  "Moderate rain",
    65:  "Heavy rain",
    71:  "Slight snow",
    73:  "Moderate snow",
    75:  "Heavy snow",
    80:  "Slight showers",
    81:  "Moderate showers",
    82:  "Violent showers",
    85:  "Slight snow showers",
    86:  "Heavy snow showers",
    95:  "Thunderstorm",
    96:  "Thunderstorm with hail",
    99:  "Thunderstorm with heavy hail",
}

HEATWAVE_THRESH = {
    "Pakistan":     38.0,
    "India":        40.0,
    "Afghanistan":  38.0,
    "Iran":         40.0,
    "China":        35.0,
}

FLOOD_PRECIP_MM   = 50.0
DROUGHT_DAYS      = 30
DROUGHT_PRECIP_MM = 1.0
STORM_WIND_KMH    = 60.0


def classify_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["time"])
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    df["hw_thresh"] = df["country"].map(HEATWAVE_THRESH).fillna(38.0)
    df["is_heatwave"] = df["temperature_2m_max"] >= df["hw_thresh"]
    df["is_flood"]    = df["precipitation_sum"]  >= FLOOD_PRECIP_MM
    df["is_storm"]    = df["windspeed_10m_max"]  >= STORM_WIND_KMH
    df["wmo_desc"]    = df["weathercode"].map(WMO_CODES).fillna("Unknown")

    df["event_type"] = "Normal"
    df.loc[df["is_heatwave"], "event_type"] = "Heatwave"
    df.loc[df["is_flood"],    "event_type"] = "Flood"
    df.loc[df["is_storm"],    "event_type"] = "Storm"
    df.loc[df["is_heatwave"] & df["is_flood"],  "event_type"] = "Heatwave+Flood"
    df.loc[df["is_heatwave"] & df["is_storm"],  "event_type"] = "Heatwave+Storm"

    return df


def extract_rainfall_events(df: pd.DataFrame) -> pd.DataFrame:
    rain = df[df["precipitation_sum"] > 0].copy()
    rain["intensity"] = pd.cut(
        rain["precipitation_sum"],
        bins=[0, 5, 15, 30, 50, 999],
        labels=["Trace", "Light", "Moderate", "Heavy", "Extreme"],
        right=True,
    )
    return rain[["date", "city", "district", "country", "lat", "lon",
                 "precipitation_sum", "intensity", "event_type"]].rename(
        columns={"precipitation_sum": "rainfall_mm"}
    )


def extract_temperature_events(df: pd.DataFrame) -> pd.DataFrame:
    return df[["date", "city", "district", "country", "lat", "lon",
               "temperature_2m_max", "temperature_2m_min",
               "temperature_2m_mean", "is_heatwave", "event_type"]].copy()


def extract_wind_events(df: pd.DataFrame) -> pd.DataFrame:
    wind = df[df["windspeed_10m_max"] > 20].copy()
    wind["severity"] = pd.cut(
        wind["windspeed_10m_max"],
        bins=[20, 40, 60, 90, 9999],
        labels=["Breezy", "Windy", "Strong", "Storm"],
        right=True,
    )
    return wind[["date", "city", "district", "country", "lat", "lon",
                 "windspeed_10m_max", "winddirection_10m_dominant",
                 "severity", "event_type"]].rename(
        columns={"windspeed_10m_max": "wind_speed_kmh"}
    )


def detect_droughts(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (city, country), grp in df.groupby(["city", "country"]):
        grp = grp.sort_values("date").reset_index(drop=True)
        dry = grp["precipitation_sum"].fillna(0) < DROUGHT_PRECIP_MM
        streak = 0
        start_date = None
        for i, is_dry in enumerate(dry):
            if is_dry:
                if streak == 0:
                    start_date = grp.loc[i, "date"]
                streak += 1
            else:
                if streak >= DROUGHT_DAYS:
                    records.append({
                        "start_date":  start_date,
                        "end_date":    grp.loc[i - 1, "date"],
                        "duration_days": streak,
                        "city":        city,
                        "district":    grp.loc[i, "district"],
                        "country":     country,
                        "lat":         grp.loc[i, "lat"],
                        "lon":         grp.loc[i, "lon"],
                        "event_type":  "Drought",
                    })
                streak = 0
        if streak >= DROUGHT_DAYS:
            records.append({
                "start_date":  start_date,
                "end_date":    grp.loc[len(grp) - 1, "date"],
                "duration_days": streak,
                "city":        city,
                "district":    grp.loc[0, "district"],
                "country":     country,
                "lat":         grp.loc[0, "lat"],
                "lon":         grp.loc[0, "lon"],
                "event_type":  "Drought",
            })
    return pd.DataFrame(records)


def compute_climate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby(["country", "city", "district", "year"]).agg(
        avg_temp_max   = ("temperature_2m_max",  "mean"),
        avg_temp_min   = ("temperature_2m_min",  "mean"),
        total_precip   = ("precipitation_sum",   "sum"),
        max_wind       = ("windspeed_10m_max",   "max"),
        heatwave_days  = ("is_heatwave",         "sum"),
        flood_days     = ("is_flood",            "sum"),
        storm_days     = ("is_storm",            "sum"),
        extreme_days   = ("event_type",          lambda x: (x != "Normal").sum()),
    ).reset_index()
    return agg


def run(raw_path: str = "data/weather_raw.csv"):
    df_raw = pd.read_csv(raw_path)
    df = classify_events(df_raw)

    out = Path("outputs")
    out.mkdir(exist_ok=True)

    rainfall  = extract_rainfall_events(df)
    temp      = extract_temperature_events(df)
    wind      = extract_wind_events(df)
    droughts  = detect_droughts(df)
    indicators = compute_climate_indicators(df)

    rainfall.to_csv(out / "rainfall_events.csv",    index=False)
    temp.to_csv(out / "temperature_events.csv",     index=False)
    wind.to_csv(out / "wind_events.csv",            index=False)
    droughts.to_csv(out / "drought_events.csv",     index=False)
    indicators.to_csv(out / "climate_indicators.csv", index=False)

    print(f"Rainfall events:     {len(rainfall)}")
    print(f"Temperature records: {len(temp)}")
    print(f"Wind events:         {len(wind)}")
    print(f"Drought events:      {len(droughts)}")
    print(f"Climate indicators:  {len(indicators)}")

    return df, rainfall, temp, wind, droughts, indicators


if __name__ == "__main__":
    run()
