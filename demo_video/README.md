# Demo

**Video:** [Watch the walkthrough](PASTE_YOUR_VIDEO_LINK_HERE)

## What the walkthrough covers

1. **Architecture**
   - The four-stage pipeline: collection, entity extraction, graph construction, analytics
   - Module responsibilities in `src/`
2. **Data collection**
   - `python src/collect_weather.py`
   - Produces `data/weather_raw.csv` (20,440 rows)
3. **Entity extraction**
   - `python src/extract_entities.py`
   - Writes the event and indicator CSVs to `outputs/`
4. **Knowledge graph in Neo4j Browser**
   - `python src/build_graph.py`
   - Node labels, relationship types, and locations in neighbouring countries (e.g. Kabul, Tehran)
5. **Analytical queries**
   - Q1: districts with the highest rainfall
   - Q5: most vulnerable districts
6. **Scope and limitations**
   - Full pipeline runs end to end for all five countries
   - Not included: a production Neo4j cluster or hourly granularity
