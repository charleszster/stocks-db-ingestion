from __future__ import annotations

from src.ingest.validate_base import ValidationResult
from src.ingest.validate.corporate_actions import validate_corporate_actions

import os
import sys
import psycopg2
from typing import Dict, List

from common import getenv
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# Configuration
# -----------------------------

SCHEMA = os.getenv("STOCKS_SCHEMA", "stocks_research")

JOBS: Dict[str, Dict[str, List[str]]] = {
    "prices_daily": {
        "requires_tables": [
            "companies",
            "securities",
            "ticker_history",
            "prices_daily",
        ],
        "orphan_checks": [
            ("prices_daily", "security_id", "securities"),
        ],
    },
    "corporate_actions": {
        "requires_tables": [
            "companies",
            "securities",
            "ticker_history",
            "corporate_actions",
        ],
        "orphan_checks": [
            ("corporate_actions", "security_id", "securities"),
        ],
    },
}


# -----------------------------
# Utility checks
# -----------------------------

def table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema, table),
    )
    return cur.fetchone() is not None


def require_tables_exist(cur, schema: str, tables: List[str]):
    for t in tables:
        if not table_exists(cur, schema, t):
            raise RuntimeError(f"Missing required table: {schema}.{t}")
        print(f"✔ table exists: {schema}.{t}")


def require_nonempty_table(cur, schema: str, table: str):
    cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
    count = cur.fetchone()[0]
    if count == 0:
        raise RuntimeError(f"{schema}.{table} is empty")
    print(f"✔ {schema}.{table} has {count} rows")


def require_active_tickers(cur, schema: str):
    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {schema}.ticker_history
        WHERE end_date IS NULL
        """
    )
    count = cur.fetchone()[0]
    if count == 0:
        raise RuntimeError("No active tickers found in ticker_history")
    print(f"✔ {count} active tickers found")


def require_unique_ticker_resolution(cur, schema: str):
    cur.execute(
        f"""
        SELECT ticker, COUNT(DISTINCT security_id)
        FROM {schema}.ticker_history
        WHERE end_date IS NULL
        GROUP BY ticker
        HAVING COUNT(DISTINCT security_id) != 1
        """
    )
    rows = cur.fetchall()
    if rows:
        examples = ", ".join(f"{t}({c})" for t, c in rows[:5])
        raise RuntimeError(
            "Ticker resolution error: each active ticker must map to exactly one "
            f"security_id. Examples: {examples}"
        )
    print("✔ all active tickers resolve to exactly one security_id")


def require_no_orphans(
    cur,
    schema: str,
    table: str,
    fk_col: str,
    ref_table: str,
):
    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {schema}.{table} t
        LEFT JOIN {schema}.{ref_table} r
          ON t.{fk_col} = r.{fk_col}
        WHERE r.{fk_col} IS NULL
        """
    )
    count = cur.fetchone()[0]
    if count != 0:
        raise RuntimeError(
            f"{schema}.{table} contains {count} orphaned rows "
            f"(missing {ref_table}.{fk_col})"
        )
    print(f"✔ no orphaned rows in {schema}.{table}")


# -----------------------------
# Job validation
# -----------------------------

def validate_job(job_name: str):
    if job_name not in JOBS:
        raise RuntimeError(
            f"Unknown job '{job_name}'. Known jobs: {', '.join(JOBS.keys())}"
        )

    cfg = JOBS[job_name]

    dsn = getenv("PG_DSN")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            print(f"\nValidating Phase-3 invariants for job: {job_name}\n")

            # Structural checks
            require_tables_exist(cur, SCHEMA, cfg["requires_tables"])

            # Identity sanity
            require_nonempty_table(cur, SCHEMA, "companies")
            require_nonempty_table(cur, SCHEMA, "securities")
            require_active_tickers(cur, SCHEMA)
            require_unique_ticker_resolution(cur, SCHEMA)

            # FK integrity
            for table, fk_col, ref_table in cfg.get("orphan_checks", []):
                require_no_orphans(cur, SCHEMA, table, fk_col, ref_table)

            print(f"\nSAFE TO RUN: {job_name}\n")

    finally:
        conn.close()


# -----------------------------
# CLI entrypoint
# -----------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m src.ingest.validate <job_name>")
        sys.exit(1)

    job_name = sys.argv[1]

    try:
        validate_job(job_name)
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
