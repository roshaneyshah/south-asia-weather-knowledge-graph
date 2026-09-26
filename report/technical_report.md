# Technical Report: Weather Intelligence Knowledge Graph

June 2026

## 1. Methodology

The pipeline follows a four-stage architecture:

**Stage 1: Collection.** Daily weather records are fetched from the Open-Meteo historical archive API for 28 cities across five countries. The API requires no key and supports arbitrary lat/lon queries. Variables fetched: maximum, minimum, and mean temperature; precipitation sum; maximum wind speed; dominant wind direction; WMO weather code; and reference evapotranspiration. The date range covers 2022-01-01 to 2023-12-31, yielding 730 records per city and 20,440 total rows.

**Stage 2: Entity extraction.** Records are classified into typed events using threshold rules:

- **Heatwave:** daily max temperature exceeds a country-specific threshold (38C for Pakistan, 40C for India/Iran, 35C for China)
- **Flood:** daily precipitation >= 50 mm
- **Wind event:** max wind speed > 20 km/h, further classified as Breezy/Windy/Strong/Storm
- **Drought:** consecutive dry streak of 30+ days (daily precipitation < 1 mm)
- **Climate indicator:** annual aggregates per city (total precipitation, mean max temperature, heatwave days, flood days, storm days, extreme event days)

**Stage 3: Graph construction.** A Neo4j property graph is built using the official Python driver. Nodes are created for countries, locations, events, dates, and climate indicators. Relationships are established both within-event-type (temporal PRECEDED/FOLLOWED chains for rainfall) and cross-domain (UPSTREAM_OF for nine geographically motivated city pairs, ASSOCIATED_WITH for co-occurring events on the same date and location).

**Stage 4: Analytics.** Six Cypher queries answer the analytical questions below. Results are saved as JSON for reproducibility.

## 2. Architecture

```
Open-Meteo API
      |
      v
collect_weather.py
  (28 cities x 730 days = 20,440 rows)
      |
      v
data/weather_raw.csv
      |
      v
extract_entities.py
  - classify_events()       -> event_type column
  - extract_rainfall_events()
  - extract_temperature_events()
  - extract_wind_events()
  - detect_droughts()
  - compute_climate_indicators()
      |
      v
outputs/*.csv (5 entity tables)
      |
      v
build_graph.py
  - load_countries_and_locations()
  - load_rainfall_events()
  - load_temperature_events()
  - load_wind_events()
  - load_droughts()
  - load_climate_indicators()
  - create_temporal_relationships()
  - create_upstream_relationships()
  - create_co_occurrence_relationships()
      |
      v
Neo4j Property Graph
  21,929 nodes | 30,119 relationships
      |
      v
analytics.py  ->  outputs/analytical_results.json
```

## 3. Knowledge Graph Schema

### Node labels and properties

| Label | Key properties |
|---|---|
| Country | name |
| Location | name, district, lat, lon |
| Date | value (YYYY-MM-DD) |
| RainfallEvent | event_id, date, rainfall_mm, intensity, event_type |
| FloodEvent | event_id, date, rainfall_mm |
| HeatwaveEvent | event_id, date, temp_max |
| TemperatureEvent | event_id, date, temp_max, temp_min, temp_mean |
| WindEvent | event_id, date, wind_speed_kmh, direction, severity |
| DroughtEvent | event_id, start_date, end_date, duration_days |
| ClimateIndicator | indicator_id, year, avg_temp_max, total_precipitation_mm, heatwave_days, flood_days, storm_days, extreme_event_days |

### Relationship types

| Relationship | From -> To | Cardinality |
|---|---|---|
| LOCATED_IN | Location -> Country | Many-to-one |
| OCCURRED_IN | Any event -> Location | Many-to-one |
| AFFECTED | FloodEvent, DroughtEvent -> Location | Many-to-one |
| CAUSED | RainfallEvent -> FloodEvent | One-to-one |
| CAUSED | TemperatureEvent -> HeatwaveEvent | One-to-one |
| ON_DATE | RainfallEvent, WindEvent -> Date | Many-to-one |
| HAS_INDICATOR | Location -> ClimateIndicator | One-to-many |
| ASSOCIATED_WITH | RainfallEvent -> HeatwaveEvent (same date/location) | Many-to-many |
| UPSTREAM_OF | RainfallEvent -> RainfallEvent (cross-border) | Many-to-many |
| PRECEDED | RainfallEvent -> RainfallEvent (within 3 days) | Many-to-many |
| FOLLOWED | RainfallEvent -> RainfallEvent (inverse) | Many-to-many |

## 4. Results

### Graph statistics

| Metric | Value |
|---|---|
| Total nodes | 21,929 |
| Total relationships | 30,119 |
| Countries | 5 (Pakistan, India, Afghanistan, Iran, China) |
| Cities | 28 |
| Date range | 2022-01-01 to 2023-12-31 |
| Heatwave events | 4,331 |
| Rainfall events | 6,624 |
| Flood events | 18 |
| Drought events | 56 |
| Wind events | 5,750 |
| Climate indicators | 56 |

### Analytical findings

**Q1: Highest rainfall districts.** Mumbai, Lahore, and Muzaffarabad consistently record the highest total precipitation over the two-year period. Mumbai benefits from the Arabian Sea monsoon; Muzaffarabad and Rawalpindi receive heavy orographic rainfall from westerly disturbances interacting with the Himalayan foothills.

**Q2: Multiple extreme event types.** Karachi shows the highest co-occurrence of heatwaves and drought events. Islamabad and Lahore record both heatwave and flood events, consistent with the pre-monsoon heat followed by intense monsoon rainfall pattern.

**Q3: Co-occurring patterns.** RainfallEvent and HeatwaveEvent co-occur most frequently, reflecting periods where the monsoon onset produces both precipitation and high humidity-driven apparent temperature extremes. WindEvent and RainfallEvent co-occur during cyclonic systems approaching the Arabian coast.

**Q4: Increasing trends.** Average maximum temperature shows a
