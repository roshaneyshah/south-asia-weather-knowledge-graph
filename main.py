import sys
import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Weather Intelligence Knowledge Graph Pipeline")
    p.add_argument("--neo4j-uri",  default="bolt://localhost:7687")
    p.add_argument("--neo4j-user", default="neo4j")
    p.add_argument("--neo4j-pass", default="password")
    p.add_argument("--skip-collect", action="store_true",
                   help="Skip API collection if data/weather_raw.csv already exists")
    p.add_argument("--skip-graph",   action="store_true",
                   help="Skip graph build, run analytics only")
    return p.parse_args()


def main():
    args = parse_args()

    raw_path = Path("data/weather_raw.csv")

    if not args.skip_collect:
        print("=" * 50)
        print("Step 1: Collecting weather data from Open-Meteo")
        print("=" * 50)
        from src.collect_weather import main as collect
        collect()
    else:
        print("Skipping collection (--skip-collect set).")

    if not raw_path.exists():
        print("ERROR: data/weather_raw.csv not found. Run without --skip-collect first.")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Step 2: Extracting entities and classifying events")
    print("=" * 50)
    from src.extract_entities import run as extract
    extract(str(raw_path))

    if not args.skip_graph:
        print("\n" + "=" * 50)
        print("Step 3: Building Neo4j knowledge graph")
        print("=" * 50)
        from src.build_graph import build_graph
        stats = build_graph(args.neo4j_uri, args.neo4j_user, args.neo4j_pass)

        print("\n" + "=" * 50)
        print("Step 4: Running analytical queries")
        print("=" * 50)
        from src.analytics import WeatherAnalytics
        analytics = WeatherAnalytics(args.neo4j_uri, args.neo4j_user, args.neo4j_pass)
        analytics.run_all()
        analytics.close()
    else:
        print("Skipping graph build (--skip-graph set).")

    print("\nPipeline complete. Check outputs/ for results.")


if __name__ == "__main__":
    main()
