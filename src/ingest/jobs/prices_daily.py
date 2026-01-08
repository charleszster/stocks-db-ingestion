from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import date
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import execute_batch

from common import getenv, requests_get_json, iso_years_ago, iso_today

"""
Phase: 3
Job: prices_daily
Requires:
  - companies
  - securities
  - ticker_history
Writes:
  - prices_daily
"""

BASE_URL = "https://api.massive.com"
SCHEMA = os.getenv("STOCKS_SCHEMA", "stocks_research")
YEARS = int(os.getenv("YEARS", "5"))

AGGS_PATH = "/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"


def load_tickers() -> List[str]:
    """
    Load the selected universe produced by bootstrap.
    """
    repo_root = Path(__file__).resolve().parents[3]
    rel = os.getenv("UNIVERSE_SELECTED", "config/universe_selected.json")
    path = (repo_root / rel).resolve()

    if not path.exists():
        raise RuntimeError(f"Universe selection file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        tickers = json.load(f)

    if not tickers:
        raise RuntimeError("Universe selection file is empty")

    return tickers


def security_id_for_ticker(cur, ticker: str) -> int:
    sql = f"""
    SELECT th.security_id
    FROM {SCHEMA}.ticker_history th
    WHERE th.ticker = %s
    ORDER BY th.start_date DESC
    LIMIT 1;
    """
    cur.execute(sql, (ticker,))
    r = cur.fetchone()
    if not r:
        raise RuntimeError(f"No security_id found for ticker {ticker}. Run 00_bootstrap_universe.py first.")
    return int(r[0])


def fetch_daily_bars(api_key: str, ticker: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    url = BASE_URL + AGGS_PATH.format(ticker=ticker, from_date=from_date, to_date=to_date)
    params = {"adjusted": "false", "sort": "asc", "limit": 50000}  # raw/unadjusted
    out: List[Dict[str, Any]] = []

    while True:
        j = requests_get_json(url, params=params, api_key=api_key)
        out.extend(j.get("results") or [])
        next_url = j.get("next_url")
        if not next_url:
            break
        url = next_url
        params = {}
    return out


def upsert_prices(conn, ticker: str, bars: List[Dict[str, Any]]) -> int:
    if not bars:
        return 0

    sql = f"""
    INSERT INTO {SCHEMA}.prices_daily (security_id, trade_date, open, high, low, close, volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (security_id, trade_date) DO UPDATE SET
      open=EXCLUDED.open,
      high=EXCLUDED.high,
      low=EXCLUDED.low,
      close=EXCLUDED.close,
      volume=EXCLUDED.volume;
    """

    with conn.cursor() as cur:
        sid = security_id_for_ticker(cur, ticker)

        rows = []
        for b in bars:
            ts_ms = int(b["t"])
            d = date.fromtimestamp(ts_ms / 1000).isoformat()
            rows.append((sid, d, b.get("o"), b.get("h"), b.get("l"), b.get("c"), int(b.get("v") or 0)))

        execute_batch(cur, sql, rows, page_size=5000)

    conn.commit()
    return len(bars)


def _run_prices_daily(conn):
    api_key = getenv("MASSIVE_API_KEY")

    tickers = load_tickers()
    from_date = iso_years_ago(YEARS)
    to_date = iso_today()

    total = 0
    for i, t in enumerate(tickers, 1):
        bars = fetch_daily_bars(api_key, t, from_date, to_date)
        n = upsert_prices(conn, t, bars)
        total += n
        print(f"{i:>2}/{len(tickers)} {t}: {n} daily bars inserted/updated")

    print(f"Done. Total bars inserted/updated: {total}")


def run(conn, job_id=None):
    """
    Phase-3 ingestion entrypoint.
    The runner owns the DB connection.
    """
    _run_prices_daily(conn)



if __name__ == "__main__":
    dsn = getenv("PG_DSN")
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        _run_prices_daily(conn)
    finally:
        conn.close()

