# Demo Video

**Link:** [Add your unlisted YouTube / Google Drive / Loom link here before submission]

## What the video covers (5-10 minutes)

1. Architecture walkthrough (1-2 min)
   - Overview of the four-stage pipeline
   - Show the src/ directory and module responsibilities

2. Live data collection (1 min)
   - Run: `python src/collect_weather.py`
   - Show weather_raw.csv being created with 20,440 rows

3. Entity extraction (1 min)
   - Run: `python src/extract_entities.py`
   - Show the five output CSVs in outputs/

4. Knowledge graph in Neo4j Browser (2 min)
   - Run: `python src/build_graph.py`
   - Open Neo4j Browser, show node labels and relationship types
   - Show at least one location from a neighbouring country (e.g. Kabul, Tehran)

5. Live analytical queries (2 min)
   - Run Q1 (highest rainfall districts) live in Neo4j Browser
   - Run Q5 (most vulnerable districts) live in Neo4j Browser

6. Summary (30 sec)
   - What was completed: full pipeline end-to-end for all 5 countries
   - What was not done: production Neo4j cluster, hourly granularity
