"""
extraction/ctload.py

Loads Climate Trace CSVs and Global Carbon Project CSV into Postgres raw schema.
Run from inside the Docker app container:
    uv run python extraction/ctload.py
"""

import sys
import io
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

# Skip any single CSV file larger than this (bytes)
MAX_FILE_BYTES = 500 * 1024 * 1024

# Rows read and COPYed at a time — commit after every chunk to avoid OOM
CHUNK_SIZE = 20_000

# ─────────────────────────────────────────────
# CLIMATE TRACE FILE CLASSIFICATION
# ─────────────────────────────────────────────

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

# Global type overrides — applied to all tables
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
    "capacity_factor":    "DOUBLE PRECISION",
    "source_id":          "BIGINT",
    "emissions_mtco2":    "DOUBLE PRECISION",
}

# In confidence files, 'capacity' holds text ratings like "high"/"low"/"very high"
# so we must NOT cast it to DOUBLE PRECISION for those tables
CONFIDENCE_TYPE_OVERRIDES = {
    **GLOBAL_TYPE_OVERRIDES,
    "capacity": "TEXT",   # override: confidence rating, not a number
}


def _sanitise_col(c: str) -> str:
    return c.strip().lower().replace(" ", "_").replace("-", "_").replace("*", "_")


def _infer_pg_type(col: str, series: pd.Series, overrides: dict) -> str:
    if col in overrides:
        return overrides[col]
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    return "TEXT"


# ─────────────────────────────────────────────
# POSTGRES HELPERS
# ─────────────────────────────────────────────

def _create_table(conn: psycopg.Connection, schema_table: str, col_defs: list):
    ddl = f"""
        CREATE SCHEMA IF NOT EXISTS raw;
        DROP TABLE IF EXISTS {schema_table};
        CREATE TABLE {schema_table} ({", ".join(col_defs)});
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _copy_chunk(conn: psycopg.Connection, schema_table: str, cols: list, df: pd.DataFrame):
    """Stream one chunk into Postgres via COPY, committing immediately after."""
    quoted_cols = ", ".join(f'"{c}"' for c in cols)
    copy_sql = f"COPY {schema_table} ({quoted_cols}) FROM STDIN (FORMAT TEXT, NULL '\\N')"

    buf = io.StringIO()
    df_clean = df.where(pd.notnull(df), None)
    for row in df_clean.itertuples(index=False):
        line = "\t".join(
            "\\N" if v is None
            else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")
            for v in row
        )
        buf.write(line + "\n")
    buf.seek(0)

    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            copy.write(buf.read())

    # Commit after every chunk — prevents Postgres OOM-killing the connection
    conn.commit()


# ─────────────────────────────────────────────
# FILE LOADER
# ─────────────────────────────────────────────

def _load_file_chunked(
    conn: psycopg.Connection,
    csv_path: Path,
    schema_table: str,
    type_overrides: dict,
    table_exists: bool,
) -> bool:
    """
    Stream a CSV in chunks into schema_table using COPY.
    - If table_exists=False, creates the table from the first chunk's schema.
    - If table_exists=True, appends directly (no DROP).
    Returns True on success, False on failure.
    """
    cols = None
    rows_loaded = 0

    try:
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False)):
            chunk.columns = [_sanitise_col(c) for c in chunk.columns]
            chunk["_source_file"] = csv_path.name

            if i == 0:
                cols = list(chunk.columns)

                if not table_exists:
                    col_defs = [
                        f'"{col}" {_infer_pg_type(col, chunk[col], type_overrides)}'
                        for col in cols
                    ]
                    print(f"    Creating {schema_table} ({len(cols)} columns)...")
                    _create_table(conn, schema_table, col_defs)

            _copy_chunk(conn, schema_table, cols, chunk[cols])
            rows_loaded += len(chunk)

            if rows_loaded % 200_000 == 0:
                print(f"    ... {rows_loaded:,} rows so far")

    except Exception as e:
        print(f"    [ERROR] {csv_path.name}: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False

    print(f"    ✓ {rows_loaded:,} rows → {schema_table}")
    return True


# ─────────────────────────────────────────────
# GLOBAL CARBON PROJECT
# ─────────────────────────────────────────────

def load_gcp(conn: psycopg.Connection):
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
    col_defs = [f'"{c}" {_infer_pg_type(c, df[c], GLOBAL_TYPE_OVERRIDES)}' for c in cols]
    _create_table(conn, schema_table, col_defs)
    _copy_chunk(conn, schema_table, cols, df)
    print(f"  ✓ Done → {schema_table}")


# ─────────────────────────────────────────────
# CLIMATE TRACE
# ─────────────────────────────────────────────

def load_climate_trace(conn: psycopg.Connection):
    for sector in SECTORS:
        sector_path = CT_PATH / sector
        if not sector_path.exists():
            print(f"\n[CT] Sector folder missing, skipping: {sector_path}")
            continue

        print(f"\n[CT] Sector: {sector}")

        grouped: dict[str, list[Path]] = {label: [] for label in FILE_TYPES.values()}
        for csv_file in sorted(sector_path.glob("*.csv")):
            ftype = _detect_file_type(csv_file.stem)
            if ftype:
                grouped[ftype].append(csv_file)
            else:
                print(f"  [SKIP] Unknown pattern: {csv_file.name}")

        for ftype, files in grouped.items():
            if not files:
                continue

            schema_table = f"raw.ct_{sector}_{ftype}"
            # Confidence files need TEXT for the 'capacity' column
            overrides = CONFIDENCE_TYPE_OVERRIDES if ftype == "confidence" else GLOBAL_TYPE_OVERRIDES

            print(f"\n  [{ftype.upper()}] → {schema_table}")

            table_exists = False
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)

                if f.stat().st_size > MAX_FILE_BYTES:
                    print(f"    [SKIP] {f.name} ({size_mb:,.0f} MB) — exceeds limit")
                    continue

                print(f"    Loading {f.name} ({size_mb:.1f} MB)...")
                success = _load_file_chunked(
                    conn,
                    f,
                    schema_table,
                    type_overrides=overrides,
                    table_exists=table_exists,
                )
                # Only mark table_exists=True after a successful load
                # This prevents subsequent files appending to a half-created table
                if success:
                    table_exists = True


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

    print("\n✅ Extraction complete.")
    print("   Verify: SELECT tablename, n_live_tup FROM pg_stat_user_tables WHERE schemaname='raw' ORDER BY tablename;")


if __name__ == "__main__":
    main()