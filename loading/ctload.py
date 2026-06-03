"""
extraction/ctload.py

Loads Climate Trace CSVs and Global Carbon Project CSV into Postgres raw schema.
Run from inside the Docker app container:
    uv run python extraction/ctload.py

Strategy:
- Uses chunked CSV reading (never loads a full file into RAM)
- Uses Postgres COPY for fast bulk inserts (10-50x faster than executemany)
- Skips files over a configurable size limit
"""

import sys
import io
import csv
import pandas as pd
import psycopg
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(line_buffering=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_URL   = "postgresql://root:root@carbon-stream:5432/carbon_stream"
LANDING  = Path("/workspace/landing")
GCP_PATH = LANDING / "global_carbon_project" / "export_emissions.csv"
CT_PATH  = LANDING / "climate_trace"

# Skip any single CSV file larger than this (bytes). 500 MB default.
# The 12 GB enteric-fermentation sources file will be skipped automatically.
MAX_FILE_BYTES = 500 * 1024 * 1024

# Rows read from CSV at a time — keeps RAM flat regardless of file size
CHUNK_SIZE = 50_000

# ─────────────────────────────────────────────
# CLIMATE TRACE FILE CLASSIFICATION
# ─────────────────────────────────────────────

# Longer suffixes MUST come first so confidence/ownership aren't misclassified as sources
FILE_TYPES = {
    "emissions_sources_confidence": "confidence",
    "emissions_sources_ownership":  "ownership",
    "emissions_sources":            "sources",
    "country_emissions":            "country",
}

SECTORS = ["agriculture", "buildings", "power", "transportation", "waste"]


def _version_strip(name: str) -> str:
    return name.replace("_v5_6_0", "")


def _detect_file_type(stem: str) -> Optional[str]:
    clean = _version_strip(stem)
    for suffix, label in FILE_TYPES.items():
        if clean.endswith(suffix):
            return label
    return None


# ─────────────────────────────────────────────
# COLUMN TYPE HELPERS
# ─────────────────────────────────────────────

GLOBAL_TYPE_OVERRIDES = {
    "year":               "INTEGER",
    "start_time":         "TIMESTAMP",
    "end_time":           "TIMESTAMP",
    "created_date":       "TIMESTAMP",
    "modified_date":      "TIMESTAMP",
    "emissions_quantity": "DOUBLE PRECISION",
    "lat":                "DOUBLE PRECISION",
    "lon":                "DOUBLE PRECISION",
    "activity":           "DOUBLE PRECISION",
    "emissions_factor":   "DOUBLE PRECISION",
    "capacity":           "DOUBLE PRECISION",
    "capacity_factor":    "DOUBLE PRECISION",
    "source_id":          "BIGINT",
    "emissions_mtco2":    "DOUBLE PRECISION",
}


def _sanitise_col(c: str) -> str:
    return c.strip().lower().replace(" ", "_").replace("-", "_").replace("*", "_")


def _infer_pg_type(col: str, series: pd.Series) -> str:
    if col in GLOBAL_TYPE_OVERRIDES:
        return GLOBAL_TYPE_OVERRIDES[col]
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    return "TEXT"


# ─────────────────────────────────────────────
# POSTGRES COPY LOADER
# ─────────────────────────────────────────────

def _create_table(conn: psycopg.Connection, schema_table: str, col_defs: list):
    """Drop and recreate a table."""
    ddl = f"""
        CREATE SCHEMA IF NOT EXISTS raw;
        DROP TABLE IF EXISTS {schema_table};
        CREATE TABLE {schema_table} ({", ".join(col_defs)});
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _copy_chunk(conn: psycopg.Connection, schema_table: str, cols: list, df: pd.DataFrame):
    """
    Stream one chunk into Postgres using COPY FROM STDIN (TEXT format).
    This is far faster than executemany and uses minimal memory.
    """
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    copy_sql = f"COPY {schema_table} ({quoted_cols}) FROM STDIN (FORMAT TEXT, NULL '\\N')"

    buf = io.StringIO()
    # Write TSV — tab-separated, NaN → \N (Postgres NULL marker)
    df_clean = df.where(pd.notnull(df), None)
    for row in df_clean.itertuples(index=False):
        line = "\t".join(
            "\\N" if v is None else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")
            for v in row
        )
        buf.write(line + "\n")
    buf.seek(0)

    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            copy.write(buf.read())


def _load_file_chunked(
    conn: psycopg.Connection,
    csv_path: Path,
    table_name: str,
    extra_col: Optional[tuple] = None,   # (col_name, value) to inject
    table_created: bool = False,
) -> bool:
    """
    Read a CSV in chunks and COPY each chunk to Postgres.
    Creates the table on the first chunk (schema inferred from sample).
    Returns True if anything was loaded.
    """
    schema_table = f"raw.{table_name}"
    cols = None
    rows_loaded = 0

    try:
        for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False):
            # Sanitise column names
            chunk.columns = [_sanitise_col(c) for c in chunk.columns]

            # Inject extra column (e.g. _source_file)
            if extra_col:
                chunk[extra_col[0]] = extra_col[1]

            if not table_created:
                cols = list(chunk.columns)
                col_defs = []
                for col in cols:
                    pg_type = _infer_pg_type(col, chunk[col])
                    col_defs.append(f'"{col}" {pg_type}')
                print(f"    Creating {schema_table} ({len(cols)} columns)...")
                _create_table(conn, schema_table, col_defs)
                table_created = True

            _copy_chunk(conn, schema_table, cols, chunk[cols])
            rows_loaded += len(chunk)

            if rows_loaded % 500_000 == 0:
                print(f"    ... {rows_loaded:,} rows loaded so far")

        conn.commit()
    except Exception as e:
        print(f"    [ERROR] Failed loading {csv_path.name}: {e}")
        conn.rollback()
        return False

    print(f"    ✓ {rows_loaded:,} rows → {schema_table}")
    return True


# ─────────────────────────────────────────────
# GLOBAL CARBON PROJECT
# ─────────────────────────────────────────────

def load_gcp(conn: psycopg.Connection):
    """
    GCP CSV is wide (countries as columns). We melt it to long format:
        year | country | emissions_mtco2
    GCP file is small enough to load fully into RAM.
    """
    print("\n[GCP] Reading Global Carbon Project CSV...")
    df = pd.read_csv(GCP_PATH, skiprows=1, header=0)
    df = df.rename(columns={df.columns[0]: "year"})
    df = df[pd.to_numeric(df["year"], errors="coerce").notna()]
    df["year"] = df["year"].astype(int)
    df = df.melt(id_vars="year", var_name="country", value_name="emissions_mtco2")
    df = df.dropna(subset=["emissions_mtco2"])
    df["emissions_mtco2"] = pd.to_numeric(df["emissions_mtco2"], errors="coerce")
    df = df.dropna(subset=["emissions_mtco2"])

    print(f"  → {len(df):,} rows")

    schema_table = "raw.gcp_emissions"
    cols = list(df.columns)
    col_defs = [f'"{c}" {_infer_pg_type(c, df[c])}' for c in cols]
    _create_table(conn, schema_table, col_defs)
    _copy_chunk(conn, schema_table, cols, df)
    conn.commit()
    print(f"  ✓ Done → {schema_table}")


# ─────────────────────────────────────────────
# CLIMATE TRACE
# ─────────────────────────────────────────────

def load_climate_trace(conn: psycopg.Connection):
    """
    For each sector, group CSVs by type (country/sources/confidence/ownership).
    Files over MAX_FILE_BYTES are skipped with a warning.
    Each group is streamed chunk-by-chunk into one merged Postgres table.
    """
    for sector in SECTORS:
        sector_path = CT_PATH / sector
        if not sector_path.exists():
            print(f"\n[CT] Sector folder missing, skipping: {sector_path}")
            continue

        print(f"\n[CT] Sector: {sector}")

        # Group files by type
        grouped: dict[str, list[Path]] = {label: [] for label in FILE_TYPES.values()}
        for csv_file in sorted(sector_path.glob("*.csv")):
            ftype = _detect_file_type(csv_file.stem)
            if ftype:
                grouped[ftype].append(csv_file)
            else:
                print(f"  [SKIP] Unknown pattern: {csv_file.name}")

        # Load each group
        for ftype, files in grouped.items():
            if not files:
                continue

            table_name = f"ct_{sector}_{ftype}"
            print(f"\n  [{ftype.upper()}] → raw.{table_name}")

            table_created = False
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)

                if f.stat().st_size > MAX_FILE_BYTES:
                    print(f"    [SKIP] {f.name} ({size_mb:,.0f} MB) — exceeds {MAX_FILE_BYTES // (1024*1024)} MB limit")
                    continue

                print(f"    Loading {f.name} ({size_mb:,.1f} MB)...")
                table_created = _load_file_chunked(
                    conn,
                    f,
                    table_name,
                    extra_col=("_source_file", f.name),
                    table_created=table_created,
                )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 55)
    print("Carbon-Stream: Landing Zone Extraction")
    print(f"Skipping files > {MAX_FILE_BYTES // (1024*1024)} MB")
    print("=" * 55)

    with psycopg.connect(DB_URL) as conn:
        load_gcp(conn)
        load_climate_trace(conn)

    print("\n✅ Extraction complete. Verify with:")
    print("   \\dt raw.*")
    print("   SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables WHERE schemaname='raw';")


if __name__ == "__main__":
    main()