// ============================================================
// Weather Intelligence Knowledge Graph -- Cypher Schema Export
// Run this in Neo4j Browser after loading data via build_graph.py
// ============================================================

// --- Constraints ---
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country)          REQUIRE c.name         IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location)         REQUIRE l.name         IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Date)             REQUIRE d.value        IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:RainfallEvent)    REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:TemperatureEvent) REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:WindEvent)        REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:DroughtEvent)     REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:FloodEvent)       REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:HeatwaveEvent)    REQUIRE e.event_id     IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:ClimateIndicator) REQUIRE i.indicator_id IS UNIQUE;

// --- Sample nodes (illustrative) ---
MERGE (pk:Country {name: 'Pakistan'});
MERGE (af:Country {name: 'Afghanistan'});
MERGE (in:Country {name: 'India'});
MERGE (ir:Country {name: 'Iran'});
MERGE (cn:Country {name: 'China'});

MERGE (isl:Location {name: 'Islamabad', district: 'Islamabad', lat: 33.72, lon: 73.04})
  -[:LOCATED_IN]->(pk);
MERGE (kbl:Location {name: 'Kabul', district: 'Kabul', lat: 34.53, lon: 69.17})
  -[:LOCATED_IN]->(af);

// --- Analytical queries (run after data load) ---

// Q1: Districts with highest total rainfall
MATCH (e:RainfallEvent)-[:OCCURRED_IN]->(l:Location)-[:LOCATED_IN]->(c:Country)
WITH l.district AS district, c.name AS country,
     sum(e.rainfall_mm) AS total_mm, count(e) AS events
ORDER BY total_mm DESC LIMIT 15
RETURN district, country, total_mm, events;

// Q2: Locations with multiple extreme event types
MATCH (l:Location)-[:LOCATED_IN]->(c:Country)
OPTIONAL MATCH (hw:HeatwaveEvent)-[:OCCURRED_IN]->(l)
OPTIONAL MATCH (fl:FloodEvent)-[:AFFECTED]->(l)
OPTIONAL MATCH (dr:DroughtEvent)-[:OCCURRED_IN]->(l)
WITH l.name AS location, c.name AS country,
     count(DISTINCT hw) + count(DISTINCT fl) + count(DISTINCT dr) AS total_extreme
WHERE total_extreme > 0
ORDER BY total_extreme DESC LIMIT 15
RETURN location, country, total_extreme;

// Q3: Co-occurring weather patterns
MATCH (e1)-[:ASSOCIATED_WITH]->(e2)
WITH labels(e1)[0] AS type1, labels(e2)[0] AS type2, count(*) AS co_count
ORDER BY co_count DESC
RETURN type1, type2, co_count;

// Q4: Year-over-year temperature trend
MATCH (l:Location)-[:HAS_INDICATOR]->(i:ClimateIndicator)
WITH l.name AS location, i.year AS year, avg(i.avg_temp_max) AS avg_tmax
ORDER BY location, year
RETURN location, year, avg_tmax;

// Q5: Most vulnerable districts (highest extreme event days)
MATCH (l:Location)-[:HAS_INDICATOR]->(i:ClimateIndicator)
WITH l.name AS location,
     sum(i.heatwave_days) AS hw, sum(i.flood_days) AS fl,
     sum(i.extreme_event_days) AS total
ORDER BY total DESC LIMIT 15
RETURN location, hw, fl, total;

// Q6: Cross-border upstream rainfall signals
MATCH (e1:RainfallEvent)-[u:UPSTREAM_OF]->(e2:RainfallEvent)
MATCH (e1)-[:OCCURRED_IN]->(l1:Location)-[:LOCATED_IN]->(c1:Country)
MATCH (e2)-[:OCCURRED_IN]->(l2:Location)-[:LOCATED_IN]->(c2:Country)
WHERE c2.name = 'Pakistan'
WITH u.upstream_loc AS upstream, c1.name AS from_country,
     u.downstream_loc AS downstream, u.typical_lag_days AS lag,
     count(*) AS pairs
ORDER BY pairs DESC
RETURN upstream, from_country, downstream, lag, pairs;