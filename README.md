# Carbon-Stream
An end-to-end data engineering pipeline and Power BI dashboard for real-time monitoring of global $CO_2$ emission trends using SQL, Python, and automated ETL workflows

## Problem Statement
National carbon emission inventories are typically reported as annual totals, providing a high-level view of a country's climate impact. However, these aggregated figures obscure critical dynamics: seasonal variations, the influence of weather on energy demand and renewable generation, and the effect of atmospheric transport on measured CO₂ concentrations. This lack of temporal and explanatory resolution makes it difficult to:
1. Compare emissions trends across countries on an apples‑to‑apples basis when weather patterns differ significantly.
2. Attribute observed changes in atmospheric CO₂ to either human activity or natural climate variability (e.g., a cold winter vs. increased fossil fuel use).
3. Identify blindspots in emission estimates, such as the underrepresentation of methane from agriculture or nitrous oxide from fertilizer use.

# Start docs server
docker exec -w /workspace/carbon_stream app dbt docs serve --host 0.0.0.0 --port 8000

# Open in browser
http://localhost:8000
