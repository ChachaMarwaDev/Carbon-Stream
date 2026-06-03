"""
extraction/world_bank.py

Pulls World Bank indicators into the carbon_stream Postgres database.
Run from inside the Docker app container:
    uv run python extraction/world_bank.py

Tables created (or replaced) in schema: raw
    raw.wb_emissions      — CO₂, methane, nitrous oxide by country/year
    raw.wb_context        — GDP, population, energy use, renewables by country/year
"""

import wbdata
import pandas as pd
import psycopg
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_URL = "postgresql://root:root@carbon-stream:5432/carbon_stream"

# Year range to pull — World Bank data goes up to ~2 years behind current year
DATE_RANGE = (
    datetime(1990, 1, 1),
    datetime(2025, 12, 31)
)

# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────

# Core emissions — what was actually emitted
EMISSIONS_INDICATORS = {
    "EN.GHG.CO2.MT.CE.AR5":    "co2_kt",           # Total CO₂ in Mt CO2e
    "EN.GHG.CO2.PC.CE.AR5":    "co2_per_capita",   # CO₂ per capita (t CO2e)
    "EN.GHG.CH4.MT.CE.AR5":    "methane_kt",       # Methane emissions (Mt CO2e) 
    "EN.GHG.N2O.MT.CE.AR5":    "nitrous_oxide_kt", # Nitrous oxide emissions (Mt CO2e)
}

# Context — why emissions changed
CONTEXT_INDICATORS = {
    "NY.GDP.MKTP.CD":          "gdp_usd",          # GDP (current US$)
    "SP.POP.TOTL":             "population",       # Population, total
    "EG.USE.PCAP.KG.OE":       "energy_use_pc",    # Energy use per capita
    "EG.ELC.RNEW.ZS":          "renewable_pct",    # Renewable electricity output (%)
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def fetch_indicators(indicators: dict, date_range: tuple) -> pd.DataFrame:
    """
    Pull a dict of {indicator_code: column_name} from World Bank API.
    Returns a tidy DataFrame with columns: country, country_code, year, <indicator columns>
    """
    print(f"  Fetching: {list(indicators.values())}")

    df = wbdata.get_dataframe(
        indicators,
        data_date=DATE_RANGE,
        source=2
    )

    # wbdata returns a MultiIndex: (country, date)
    df = df.reset_index()
    df = df.rename(columns={"country": "country", "date": "year"})

    # Keep only the year part — we don't need month/day (all annual data)
    df["year"] = pd.to_datetime(df["year"]).dt.year

    # Drop rows where every indicator value is null (country/year with no data)
    value_cols = list(indicators.values())
    df = df.dropna(how="all", subset=value_cols)

    # Add a country_code column — wbdata exposes it via get_country()
    # For simplicity we'll derive it from the country name via a separate call
    # (wbdata.get_dataframe doesn't return ISO codes by default)
    print(f"  → {len(df):,} rows fetched")
    return df


def add_country_codes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds iso2_code and iso3_code columns by joining against wbdata's country list.
    """
    print("  Fetching country metadata for ISO codes...")
    countries = wbdata.get_country()  # source=2 = World Development Indicators

    # Build a lookup: country name → codes
    code_map = {
        c["name"]: {
            "iso2_code": c.get("iso2Code", ""),
            "iso3_code": c.get("id", ""),       # 'id' is the 3-letter code
            "region":    c.get("region", {}).get("value", ""),
            "income_level": c.get("incomeLevel", {}).get("value", ""),
        }
        for c in countries
    }

    lookup_df = pd.DataFrame.from_dict(code_map, orient="index").reset_index()
    lookup_df = lookup_df.rename(columns={"index": "country"})

    df = df.merge(lookup_df, on="country", how="left")
    return df


def load_to_postgres(df: pd.DataFrame, table_name: str, conn: psycopg.Connection):
    """
    Drops and recreates the table, then bulk-inserts all rows.
    Uses raw schema so dbt can pick it up cleanly.
    """
    schema_table = f"raw.{table_name}"
    cols = list(df.columns)

    # Build CREATE TABLE with appropriate types
    type_map = {
        "country":       "TEXT",
        "iso2_code":     "TEXT",
        "iso3_code":     "TEXT",
        "region":        "TEXT",
        "income_level":  "TEXT",
        "year":          "INTEGER",
    }
    col_defs = []
    for col in cols:
        pg_type = type_map.get(col, "DOUBLE PRECISION")
        col_defs.append(f'"{col}" {pg_type}')

    ddl = f"""
        CREATE SCHEMA IF NOT EXISTS raw;
        DROP TABLE IF EXISTS {schema_table};
        CREATE TABLE {schema_table} (
            {", ".join(col_defs)}
        );
    """

    print(f"  Creating table {schema_table}...")
    with conn.cursor() as cur:
        cur.execute(ddl)

    # Bulk insert via COPY — much faster than row-by-row INSERT
    # psycopg3's copy() method streams data efficiently
    placeholders = ", ".join([f"%({col})s" for col in cols])
    insert_sql = f'INSERT INTO {schema_table} ({", ".join(f"{chr(34)}{c}{chr(34)}" for c in cols)}) VALUES ({placeholders})'

    rows = df.where(pd.notnull(df), None).to_dict(orient="records")

    print(f"  Loading {len(rows):,} rows into {schema_table}...")
    with conn.cursor() as cur:
        cur.executemany(insert_sql, rows)

    conn.commit()
    print(f"  ✓ Done → {schema_table}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 55)
    print("Carbon-Stream: World Bank Extraction")
    print("=" * 55)

    # ── 1. Fetch emissions data ──────────────────────
    print("\n[1/4] Fetching emissions indicators...")
    emissions_df = fetch_indicators(EMISSIONS_INDICATORS, DATE_RANGE)

    # ── 2. Fetch context data ────────────────────────
    print("\n[2/4] Fetching context indicators...")
    context_df = fetch_indicators(CONTEXT_INDICATORS, DATE_RANGE)

    # ── 3. Add ISO country codes to both ────────────
    print("\n[3/4] Adding country codes...")
    emissions_df = add_country_codes(emissions_df)
    context_df   = add_country_codes(context_df)

    # Reorder columns so the key fields come first
    key_cols = ["country", "iso2_code", "iso3_code", "region", "income_level", "year"]
    emissions_df = emissions_df[key_cols + list(EMISSIONS_INDICATORS.values())]
    context_df   = context_df[key_cols + list(CONTEXT_INDICATORS.values())]

    # ── 4. Load into Postgres ────────────────────────
    print("\n[4/4] Loading into Postgres...")
    with psycopg.connect(DB_URL) as conn:
        load_to_postgres(emissions_df, "wb_emissions", conn)
        load_to_postgres(context_df,   "wb_context",   conn)

    print("\n✅ World Bank extraction complete.")
    print("   Tables ready:")
    print("     raw.wb_emissions  — CO₂, methane, nitrous oxide")
    print("     raw.wb_context    — GDP, population, energy use, renewables")


if __name__ == "__main__":
    main()