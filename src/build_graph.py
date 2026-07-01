import pandas as pd
import numpy as np
from pathlib import Path
from neo4j import GraphDatabase
from datetime import timedelta
import json


class WeatherKG:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def _run(self, query: str, params: dict = None):
        with self.driver.session() as session:
            return session.run(query, params or {})

    def clear(self):
        self._run("MATCH (n) DETACH DELETE n")
        print("Graph cleared.")

    def create_constraints(self):
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country)  REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Date)     REQUIRE d.value IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:RainfallEvent)    REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:TemperatureEvent) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:WindEvent)        REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:DroughtEvent)     REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:FloodEvent)       REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:HeatwaveEvent)    REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:ClimateIndicator) REQUIRE i.indicator_id IS UNIQUE",
        ]
        for c in constraints:
            try:
                self._run(c)
            except Exception:
                pass
        print("Constraints created.")

    def load_countries_and_locations(self, df_raw: pd.DataFrame):
        countries = df_raw[["country"]].drop_duplicates()
        for _, row in countries.iterrows():
            self._run(
                "MERGE (c:Country {name: $name})",
                {"name": row["country"]},
            )

        locs = df_raw[["city", "district", "country", "lat", "lon"]].drop_duplicates(subset=["city"])
        for _, row in locs.iterrows():
            self._run(
                """
                MERGE (l:Location {name: $city})
                SET l.district = $district, l.lat = $lat, l.lon = $lon
                WITH l
                MATCH (c:Country {name: $country})
                MERGE (l)-[:LOCATED_IN]->(c)
                """,
                {"city": row["city"], "district": row["district"],
                 "country": row["country"], "lat": float(row["lat"]), "lon": float(row["lon"])},
            )
        print(f"Loaded {len(locs)} locations across {len(countries)} countries.")

    def load_rainfall_events(self, df: pd.DataFrame):
        count = 0
        for _, row in df.iterrows():
            eid = f"RAIN_{row['city']}_{row['date']}"
            params = {
                "eid":      eid,
                "date":     str(row["date"])[:10],
                "mm":       float(row["rainfall_mm"]),
                "intensity": str(row["intensity"]),
                "etype":    str(row["event_type"]),
                "city":     row["city"],
            }
            self._run(
                """
                MERGE (e:RainfallEvent {event_id: $eid})
                SET e.date = $date, e.rainfall_mm = $mm,
                    e.intensity = $intensity, e.event_type = $etype
                WITH e
                MATCH (l:Location {name: $city})
                MERGE (e)-[:OCCURRED_IN]->(l)
                WITH e
                MERGE (d:Date {value: $date})
                MERGE (e)-[:ON_DATE]->(d)
                """,
                params,
            )
            if row["event_type"] in ("Flood", "Heatwave+Flood"):
                self._run(
                    """
                    MERGE (fe:FloodEvent {event_id: $feid})
                    SET fe.date = $date, fe.rainfall_mm = $mm, fe.event_type = 'Flood'
                    WITH fe
                    MATCH (e:RainfallEvent {event_id: $eid})
                    MERGE (e)-[:CAUSED]->(fe)
                    WITH fe
                    MATCH (l:Location {name: $city})
                    MERGE (fe)-[:AFFECTED]->(l)
                    """,
                    {"feid": f"FLOOD_{row['city']}_{row['date']}", **params},
                )
            count += 1
        print(f"Loaded {count} rainfall events.")

    def load_temperature_events(self, df: pd.DataFrame):
        heatwaves = df[df["is_heatwave"] == True]
        count = 0
        for _, row in heatwaves.iterrows():
            eid = f"TEMP_{row['city']}_{row['date']}"
            params = {
                "eid":    eid,
                "date":   str(row["date"])[:10],
                "tmax":   float(row["temperature_2m_max"]),
                "tmin":   float(row["temperature_2m_min"]),
                "tmean":  float(row["temperature_2m_mean"]) if pd.notna(row["temperature_2m_mean"]) else None,
                "etype":  str(row["event_type"]),
                "city":   row["city"],
                "hweid":  f"HW_{row['city']}_{row['date']}",
            }
            self._run(
                """
                MERGE (e:TemperatureEvent {event_id: $eid})
                SET e.date = $date, e.temp_max = $tmax,
                    e.temp_min = $tmin, e.temp_mean = $tmean, e.event_type = $etype
                WITH e
                MATCH (l:Location {name: $city})
                MERGE (e)-[:OCCURRED_IN]->(l)
                WITH e
                MERGE (d:Date {value: $date})
                MERGE (e)-[:ON_DATE]->(d)
                WITH e
                MERGE (hw:HeatwaveEvent {event_id: $hweid})
                SET hw.date = $date, hw.temp_max = $tmax
                MERGE (e)-[:CAUSED]->(hw)
                """,
                params,
            )
            count += 1
        print(f"Loaded {count} temperature/heatwave events.")

    def load_wind_events(self, df: pd.DataFrame):
        count = 0
        for _, row in df.iterrows():
            eid = f"WIND_{row['city']}_{row['date']}"
            params = {
                "eid":      eid,
                "date":     str(row["date"])[:10],
                "speed":    float(row["wind_speed_kmh"]),
                "dir":      float(row["winddirection_10m_dominant"]) if pd.notna(row["winddirection_10m_dominant"]) else None,
                "severity": str(row["severity"]),
                "city":     row["city"],
            }
            self._run(
                """
                MERGE (e:WindEvent {event_id: $eid})
                SET e.date = $date, e.wind_speed_kmh = $speed,
                    e.direction = $dir, e.severity = $severity
                WITH e
                MATCH (l:Location {name: $city})
                MERGE (e)-[:OCCURRED_IN]->(l)
                WITH e
                MERGE (d:Date {value: $date})
                MERGE (e)-[:ON_DATE]->(d)
                """,
                params,
            )
            count += 1
        print(f"Loaded {count} wind events.")

    def load_droughts(self, df: pd.DataFrame):
        if df.empty:
            print("No drought events detected.")
            return
        count = 0
        for _, row in df.iterrows():
            eid = f"DROUGHT_{row['city']}_{row['start_date']}"
            params = {
                "eid":      eid,
                "start":    str(row["start_date"])[:10],
                "end":      str(row["end_date"])[:10],
                "duration": int(row["duration_days"]),
                "city":     row["city"],
            }
            self._run(
                """
                MERGE (e:DroughtEvent {event_id: $eid})
                SET e.start_date = $start, e.end_date = $end,
                    e.duration_days = $duration, e.event_type = 'Drought'
                WITH e
                MATCH (l:Location {name: $city})
                MERGE (e)-[:OCCURRED_IN]->(l)
                MERGE (e)-[:AFFECTED]->(l)
                """,
                params,
            )
            count += 1
        print(f"Loaded {count} drought events.")

    def load_climate_indicators(self, df: pd.DataFrame):
        count = 0
        for _, row in df.iterrows():
            iid = f"IND_{row['city']}_{row['year']}"
            params = {
                "iid":          iid,
                "city":         row["city"],
                "year":         int(row["year"]),
                "avg_tmax":     float(row["avg_temp_max"]) if pd.notna(row["avg_temp_max"]) else None,
                "avg_tmin":     float(row["avg_temp_min"]) if pd.notna(row["avg_temp_min"]) else None,
                "total_precip": float(row["total_precip"])  if pd.notna(row["total_precip"])  else None,
                "max_wind":     float(row["max_wind"])      if pd.notna(row["max_wind"])      else None,
                "hw_days":      int(row["heatwave_days"]),
                "flood_days":   int(row["flood_days"]),
                "storm_days":   int(row["storm_days"]),
                "extreme_days": int(row["extreme_days"]),
            }
            self._run(
                """
                MERGE (i:ClimateIndicator {indicator_id: $iid})
                SET i.year = $year, i.avg_temp_max = $avg_tmax,
                    i.avg_temp_min = $avg_tmin, i.total_precipitation_mm = $total_precip,
                    i.max_wind_kmh = $max_wind, i.heatwave_days = $hw_days,
                    i.flood_days = $flood_days, i.storm_days = $storm_days,
                    i.extreme_event_days = $extreme_days
                WITH i
                MATCH (l:Location {name: $city})
                MERGE (l)-[:HAS_INDICATOR]->(i)
                MERGE (i)-[:ASSOCIATED_WITH]->(l)
                """,
                params,
            )
            count += 1
        print(f"Loaded {count} climate indicators.")

    def create_temporal_relationships(self, df_raw: pd.DataFrame):
        df = df_raw[["city", "country"]].drop_duplicates()
        count = 0
        for _, row in df.iterrows():
            self._run(
                """
                MATCH (e1:RainfallEvent)-[:OCCURRED_IN]->(l:Location {name: $city})
                MATCH (e2:RainfallEvent)-[:OCCURRED_IN]->(l)
                WHERE e1.date < e2.date
                  AND duration.between(date(e1.date), date(e2.date)).days <= 3
                  AND e1.rainfall_mm >= 30
                  AND e2.rainfall_mm >= 30
                MERGE (e1)-[:PRECEDED]->(e2)
                MERGE (e2)-[:FOLLOWED]->(e1)
                """,
                {"city": row["city"]},
            )
            count += 1
        print(f"Created temporal relationships for {count} locations.")

    def create_upstream_relationships(self):
        upstream_pairs = [
            ("Kabul",    "Peshawar",   3),
            ("Kabul",    "Islamabad",  4),
            ("Jalalabad","Peshawar",   2),
            ("Herat",    "Quetta",     5),
            ("Zahedan",  "Quetta",     3),
            ("Srinagar", "Islamabad",  2),
            ("Amritsar", "Lahore",     1),
            ("Urumqi",   "Gilgit",     6),
            ("Kashgar",  "Gilgit",     4),
        ]
        count = 0
        for upstream, downstream, lag_days in upstream_pairs:
            self._run(
                """
                MATCH (e1:RainfallEvent)-[:OCCURRED_IN]->(l1:Location {name: $up})
                MATCH (e2:RainfallEvent)-[:OCCURRED_IN]->(l2:Location {name: $down})
                WHERE e1.rainfall_mm >= 20
                  AND e2.rainfall_mm >= 15
                  AND duration.between(date(e1.date), date(e2.date)).days >= 0
                  AND duration.between(date(e1.date), date(e2.date)).days <= $lag
                MERGE (e1)-[:UPSTREAM_OF {typical_lag_days: $lag, upstream_loc: $up, downstream_loc: $down}]->(e2)
                """,
                {"up": upstream, "down": downstream, "lag": lag_days},
            )
            count += 1
        print(f"Created upstream relationships for {count} city pairs.")

    def create_co_occurrence_relationships(self):
        self._run(
            """
            MATCH (e1:RainfallEvent)-[:OCCURRED_IN]->(l:Location)
            MATCH (e2:HeatwaveEvent)-[:OCCURRED_IN]->(l)
            WHERE e1.date = e2.date
            MERGE (e1)-[:ASSOCIATED_WITH]->(e2)
            """
        )
        self._run(
            """
            MATCH (e1:WindEvent)-[:OCCURRED_IN]->(l:Location)
            MATCH (e2:RainfallEvent)-[:OCCURRED_IN]->(l)
            WHERE e1.date = e2.date AND e1.wind_speed_kmh >= 60
            MERGE (e1)-[:ASSOCIATED_WITH]->(e2)
            """
        )
        print("Created co-occurrence relationships.")

    def get_stats(self) -> dict:
        node_count = self._run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        rel_count  = self._run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
        labels     = [r["label"] for r in self._run("CALL db.labels() YIELD label RETURN label")]
        rel_types  = [r["type"]  for r in self._run("CALL db.relationshipTypes() YIELD relationshipType AS type RETURN type")]
        return {
            "nodes":         node_count,
            "relationships": rel_count,
            "node_labels":   labels,
            "rel_types":     rel_types,
        }


def build_graph(uri="bolt://localhost:7687", user="neo4j", password="password"):
    out = Path("outputs")

    df_raw    = pd.read_csv("data/weather_raw.csv")
    rainfall  = pd.read_csv(out / "rainfall_events.csv",    parse_dates=["date"])
    temp      = pd.read_csv(out / "temperature_events.csv", parse_dates=["date"])
    wind      = pd.read_csv(out / "wind_events.csv",        parse_dates=["date"])
    droughts  = pd.read_csv(out / "drought_events.csv")
    indicators = pd.read_csv(out / "climate_indicators.csv")

    kg = WeatherKG(uri, user, password)
    kg.clear()
    kg.create_constraints()
    kg.load_countries_and_locations(df_raw)
    kg.load_rainfall_events(rainfall)
    kg.load_temperature_events(temp)
    kg.load_wind_events(wind)
    kg.load_droughts(droughts)
    kg.load_climate_indicators(indicators)
    kg.create_temporal_relationships(df_raw)
    kg.create_upstream_relationships()
    kg.create_co_occurrence_relationships()

    stats = kg.get_stats()
    print("\nGraph statistics:")
    print(f"  Nodes:         {stats['nodes']}")
    print(f"  Relationships: {stats['relationships']}")
    print(f"  Labels:        {stats['node_labels']}")
    print(f"  Rel types:     {stats['rel_types']}")

    with open(out / "graph_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    kg.close()
    return stats


if __name__ == "__main__":
    import sys
    uri  = sys.argv[1] if len(sys.argv) > 1 else "bolt://localhost:7687"
    user = sys.argv[2] if len(sys.argv) > 2 else "neo4j"
    pwd  = sys.argv[3] if len(sys.argv) > 3 else "password"
    build_graph(uri, user, pwd)
