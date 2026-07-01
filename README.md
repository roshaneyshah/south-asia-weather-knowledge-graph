# PCN-Internship-2026 — Task 2: Weather Intelligence Knowledge Graph

**Candidate:** [Your Name]
**Lab:** Parallel Computing and Networks (PCN) Research Lab, FAST-NUCES
**Task selected:** Task 2 — Weather Intelligence Knowledge Graph

---

## Overview

This project builds an end-to-end pipeline that:

1. Collects weather data from the Open-Meteo API for Pakistan and its four neighbouring countries (India, Afghanistan, Iran, China)
2. Classifies weather records into typed events: rainfall, temperature, heatwave, flood, wind, drought
3. Constructs a Neo4j knowledge graph linking locations, countries, events, dates, and climate indicators
4. Answers all six required analytical queries via Cypher

**Graph statistics (2022-2023, 28 cities, 5 countries):**

| Metric | Value |
|---|---|
| Nodes | 21,929 |
| Relationships | 30,119 |
| Countries | 5 |
| Cities | 28 |
| Date range | 2022-01-01 to 2023-12-31 |

---

## Repository Structure

```
PCN-Internship-2026-YourName/
├── README.md
├── main.py                        # Single entry point for the full pipeline
├── requirements.txt
├── src/
│   ├── collect_weather.py         # Open-Meteo API collector (falls back to synthetic if offline)
│   ├── generate_synthetic.py      # Synthetic data matching Open-Meteo schema (testing/offline)
│   ├── extract_entities.py        # Event classification and entity extraction
│   ├── build_graph.py             # Neo4j graph construction
│   ├── analytics.py               # Six analytical Cypher queries
│   └── export_schema.py           # Cypher schema export and graph summary
├── data/
│   └── weather_raw.csv            # Collected weather data (generated on first run)
├── outputs/
│   ├── rainfall_events.csv
│   ├── temperature_events.csv
│   ├── wind_events.csv
│   ├── drought_events.csv
│   ├── climate_indicators.csv
│   ├── graph_summary.json
│   ├── graph_schema.cypher        # Import-ready Cypher for Neo4j Browser
│   └── analytical_results.json    # Answers to all 6 queries
├── report/
│   └── technical_report.md
└── demo_video/
    └── README.md                  # Link to screen recording
```

---

## Setup

### Prerequisites

- Python 3.10+
- Neo4j 5.x (Community or AuraDB free tier)
- Internet access for the Open-Meteo API (no API key required)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start Neo4j

**Option A — Local:**
Download from [neo4j.com/download](https://neo4j.com/download/), start Neo4j Desktop, create a database, and note the bolt URI, username, and password.

**Option B — AuraDB (free cloud):**
Create a free instance at [console.neo4j.io](https://console.neo4j.io) and copy the connection string.

---

## Running the pipeline

### Full pipeline (API data + graph build + analytics)

```bash
python main.py \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --neo4j-pass <your-password>
```

### Skip API collection (use existing data/weather_raw.csv)

```bash
python main.py --skip-collect \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --neo4j-pass <your-password>
```

### Run individual steps

```bash
# Step 1: Collect weather data
python src/collect_weather.py

# Step 2: Extract and classify entities
python src/extract_entities.py

# Step 3: Build knowledge graph
python src/build_graph.py bolt://localhost:7687 neo4j <password>

# Step 4: Run analytical queries
python src/analytics.py bolt://localhost:7687 neo4j <password>

# Step 5: Export schema + summary
python src/export_schema.py
```

---

## Offline / no-network mode

If the Open-Meteo API is unreachable, `collect_weather.py` automatically calls `generate_synthetic.py`, which produces data in the exact same schema as the API. All downstream steps run identically.

```bash
python src/generate_synthetic.py   # writes data/weather_raw.csv
python src/extract_entities.py
python src/build_graph.py bolt://localhost:7687 neo4j <password>
```

---

## Data sources

| Country | Cities | Source |
|---|---|---|
| Pakistan | 12 | Open-Meteo archive API |
| India | 5 | Open-Meteo archive API |
| Afghanistan | 4 | Open-Meteo archive API |
| Iran | 4 | Open-Meteo archive API |
| China (Xinjiang) | 3 | Open-Meteo archive API |

Variables collected: `temperature_2m_max`, `temperature_2m_min`, `temperature_2m_mean`, `precipitation_sum`, `windspeed_10m_max`, `winddirection_10m_dominant`, `weathercode`, `et0_fao_evapotranspiration`

---

## Knowledge graph schema

### Node types

| Label | Description |
|---|---|
| `Country` | One of five countries |
| `Location` | City with lat/lon and district |
| `Date` | Calendar date (YYYY-MM-DD) |
| `RainfallEvent` | Daily precipitation record |
| `FloodEvent` | Derived when rainfall >= 50 mm/day |
| `HeatwaveEvent` | Day exceeding country-specific threshold |
| `TemperatureEvent` | All heatwave temperature records |
| `WindEvent` | Days with wind > 20 km/h |
| `DroughtEvent` | Consecutive dry streak >= 30 days |
| `ClimateIndicator` | Annual aggregate per city |

### Relationship types

| Type | Meaning |
|---|---|
| `LOCATED_IN` | Location -> Country |
| `OCCURRED_IN` | Event -> Location |
| `AFFECTED` | Event -> Location (harm-focused) |
| `CAUSED` | Rainfall -> FloodEvent; Temperature -> HeatwaveEvent |
| `ON_DATE` | Event -> Date |
| `HAS_INDICATOR` | Location -> ClimateIndicator |
| `ASSOCIATED_WITH` | Co-occurring events on same date and location |
| `UPSTREAM_OF` | Cross-border signal: neighbour event precedes Pakistan event |
| `PRECEDED` | Sequential heavy rainfall events within 3 days |
| `FOLLOWED` | Inverse of PRECEDED |

---

## Analytical queries answered

All six required queries are implemented in `src/analytics.py` and results saved to `outputs/analytical_results.json`.

| # | Query |
|---|---|
| Q1 | Districts with highest rainfall |
| Q2 | Regions with multiple extreme event types |
| Q3 | Weather patterns that co-occur frequently |
| Q4 | Climate indicators showing increasing trends |
| Q5 | Most vulnerable districts |
| Q6 | Upstream cross-border rainfall signals and typical lag |

---

## LLM usage disclosure

Claude (Anthropic) was used to assist with:

- Initial boilerplate for the Neo4j driver session setup
- Drafting WMO weather code mapping table
- Suggesting the upstream city-pair lag values based on known regional meteorology

All pipeline logic, thresholds, entity classification rules, Cypher queries, and graph schema design were authored by the candidate. All LLM-generated sections were reviewed, tested, and modified before inclusion.

---

## Demo video

Link: [Add your unlisted YouTube / Google Drive / Loom link here]

Contents:
- Architecture walkthrough
- Live API collection run
- Entity extraction output
- Knowledge graph in Neo4j Browser
- Live execution of Q1 and Q5 analytical queries
- Summary of what was completed
