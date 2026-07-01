from neo4j import GraphDatabase
import pandas as pd
import json
from pathlib import Path


class WeatherAnalytics:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def _run(self, query: str, params: dict = None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [dict(r) for r in result]

    def q1_highest_rainfall_districts(self) -> list:
        """Which districts experienced the highest rainfall?"""
        return self._run(
            """
            MATCH (e:RainfallEvent)-[:OCCURRED_IN]->(l:Location)-[:LOCATED_IN]->(c:Country)
            WITH l.district AS district, c.name AS country,
                 sum(e.rainfall_mm) AS total_mm,
                 count(e) AS event_count,
                 max(e.rainfall_mm) AS max_single_event
            ORDER BY total_mm DESC
            LIMIT 15
            RETURN district, country, total_mm, event_count, max_single_event
            """
        )

    def q2_multiple_extreme_events(self) -> list:
        """Which regions experienced multiple extreme weather events?"""
        return self._run(
            """
            MATCH (l:Location)-[:LOCATED_IN]->(c:Country)
            OPTIONAL MATCH (hw:HeatwaveEvent)-[:OCCURRED_IN]->(l)
            OPTIONAL MATCH (fl:FloodEvent)-[:AFFECTED]->(l)
            OPTIONAL MATCH (dr:DroughtEvent)-[:OCCURRED_IN]->(l)
            OPTIONAL MATCH (st:WindEvent {severity: 'Storm'})-[:OCCURRED_IN]->(l)
            WITH l.name AS location, c.name AS country,
                 count(DISTINCT hw) AS heatwave_events,
                 count(DISTINCT fl) AS flood_events,
                 count(DISTINCT dr) AS drought_events,
                 count(DISTINCT st) AS storm_events
            WITH location, country,
                 heatwave_events, flood_events, drought_events, storm_events,
                 (heatwave_events + flood_events + drought_events + storm_events) AS total_extreme
            WHERE total_extreme > 0
            ORDER BY total_extreme DESC
            LIMIT 15
            RETURN location, country, heatwave_events, flood_events,
                   drought_events, storm_events, total_extreme
            """
        )

    def q3_co_occurring_patterns(self) -> list:
        """What weather patterns frequently occur together?"""
        return self._run(
            """
            MATCH (e1)-[:ASSOCIATED_WITH]->(e2)
            WITH labels(e1)[0] AS type1, labels(e2)[0] AS type2, count(*) AS co_count
            ORDER BY co_count DESC
            RETURN type1, type2, co_count
            """
        )

    def q4_increasing_climate_trends(self) -> list:
        """Which climate indicators show increasing trends?"""
        return self._run(
            """
            MATCH (l:Location)-[:HAS_INDICATOR]->(i:ClimateIndicator)
            WITH l.name AS location,
                 collect({year: i.year, tmax: i.avg_temp_max,
                          precip: i.total_precipitation_mm,
                          extreme: i.extreme_event_days}) AS yearly
            UNWIND yearly AS y
            WITH location, y.year AS yr,
                 avg(y.tmax) AS avg_tmax, avg(y.precip) AS avg_precip,
                 avg(y.extreme) AS avg_extreme
            ORDER BY location, yr
            RETURN location, yr AS year, avg_tmax, avg_precip, avg_extreme
            """
        )

    def q5_most_vulnerable_districts(self) -> list:
        """Which districts appear most vulnerable to extreme weather?"""
        return self._run(
            """
            MATCH (l:Location)-[:HAS_INDICATOR]->(i:ClimateIndicator)
            WITH l.name AS location,
                 sum(i.heatwave_days) AS total_hw,
                 sum(i.flood_days) AS total_flood,
                 sum(i.storm_days) AS total_storm,
                 sum(i.extreme_event_days) AS total_extreme,
                 avg(i.total_precipitation_mm) AS avg_annual_precip
            ORDER BY total_extreme DESC
            LIMIT 15
            RETURN location, total_hw, total_flood, total_storm,
                   total_extreme, avg_annual_precip
            """
        )

    def q6_upstream_lag_analysis(self) -> list:
        """Do extreme weather events in neighbouring countries precede related events in Pakistan?"""
        return self._run(
            """
            MATCH (e1:RainfallEvent)-[u:UPSTREAM_OF]->(e2:RainfallEvent)
            MATCH (e1)-[:OCCURRED_IN]->(l1:Location)-[:LOCATED_IN]->(c1:Country)
            MATCH (e2)-[:OCCURRED_IN]->(l2:Location)-[:LOCATED_IN]->(c2:Country)
            WHERE c2.name = 'Pakistan'
            WITH u.upstream_loc AS upstream_city,
                 u.downstream_loc AS downstream_city,
                 c1.name AS upstream_country,
                 u.typical_lag_days AS lag_days,
                 count(*) AS event_pairs,
                 avg(e1.rainfall_mm) AS avg_upstream_mm,
                 avg(e2.rainfall_mm) AS avg_downstream_mm
            ORDER BY event_pairs DESC
            RETURN upstream_city, upstream_country, downstream_city,
                   lag_days, event_pairs, avg_upstream_mm, avg_downstream_mm
            """
        )

    def run_all(self, save_path: str = "outputs/analytical_results.json"):
        results = {
            "Q1_highest_rainfall_districts":   self.q1_highest_rainfall_districts(),
            "Q2_multiple_extreme_events":      self.q2_multiple_extreme_events(),
            "Q3_co_occurring_patterns":        self.q3_co_occurring_patterns(),
            "Q4_increasing_climate_trends":    self.q4_increasing_climate_trends(),
            "Q5_most_vulnerable_districts":    self.q5_most_vulnerable_districts(),
            "Q6_upstream_lag_analysis":        self.q6_upstream_lag_analysis(),
        }
        with open(save_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {save_path}")

        print("\n--- Q1: Top rainfall districts ---")
        for r in results["Q1_highest_rainfall_districts"][:5]:
            print(f"  {r['district']} ({r['country']}): {r['total_mm']:.1f} mm total")

        print("\n--- Q2: Regions with multiple extreme events ---")
        for r in results["Q2_multiple_extreme_events"][:5]:
            print(f"  {r['location']} ({r['country']}): {r['total_extreme']} extreme events")

        print("\n--- Q3: Co-occurring patterns ---")
        for r in results["Q3_co_occurring_patterns"]:
            print(f"  {r['type1']} + {r['type2']}: {r['co_count']} times")

        print("\n--- Q5: Most vulnerable districts ---")
        for r in results["Q5_most_vulnerable_districts"][:5]:
            print(f"  {r['location']}: {r['total_extreme']} extreme days "
                  f"({r['total_hw']} hw, {r['total_flood']} flood, {r['total_storm']} storm)")

        print("\n--- Q6: Upstream lag analysis ---")
        for r in results["Q6_upstream_lag_analysis"][:5]:
            print(f"  {r['upstream_city']} ({r['upstream_country']}) -> {r['downstream_city']}: "
                  f"{r['event_pairs']} pairs, lag {r['lag_days']} days")

        return results


if __name__ == "__main__":
    import sys
    uri  = sys.argv[1] if len(sys.argv) > 1 else "bolt://localhost:7687"
    user = sys.argv[2] if len(sys.argv) > 2 else "neo4j"
    pwd  = sys.argv[3] if len(sys.argv) > 3 else "password"
    analytics = WeatherAnalytics(uri, user, pwd)
    analytics.run_all()
    analytics.close()
