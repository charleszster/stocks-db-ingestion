from __future__ import annotations

import sys
from pathlib import Path

# Resolve repo root: scripts/bootstrap/00_bootstrap_universe.py → repo root
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))


import os
import json
from typing import Any, Dict, List, Tuple

import csv
import psycopg2
from psycopg2.extras import execute_batch

from common import getenv, requests_get_json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.massive.com"
SCHEMA = os.getenv("STOCKS_SCHEMA", "stocks_research")
TOP_N = int(os.getenv("TOP_N", "50"))
FINVIZ_ENRICH = os.getenv("FINVIZ_ENRICH", "1") == "1"

TICKER_OVERVIEW_PATH = "/v3/reference/tickers/{ticker}"


from pathlib import Path

def load_universe_tickers_from_csv() -> List[str]:
    """
    Load tickers from a CSV universe file.

    Default: config/universe_dev.csv
    Override: UNIVERSE_CSV in environment/.env
      e.g. UNIVERSE_CSV=config/universe_dev.csv
    The CSV must have a header row containing a 'ticker' column.
    """
    repo_root = Path(__file__).resolve().parents[2]
    rel = os.getenv("UNIVERSE_CSV", "config/universe_dev.csv")
    path = (repo_root / rel).resolve()

    if not path.exists():
        raise RuntimeError(f"Universe file not found: {path}")

    tickers: List[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "ticker" not in reader.fieldnames:
            raise RuntimeError(f"{path.name} must contain a 'ticker' column header")

        for row in reader:
            t = (row.get("ticker") or "").strip()
            if t:
                tickers.append(t)

    if not tickers:
        raise RuntimeError(f"{path.name} contains no tickers")

    return tickers



def get_ticker_overview(api_key: str, ticker: str) -> Dict[str, Any]:
    url = BASE_URL + TICKER_OVERVIEW_PATH.format(ticker=ticker)
    return requests_get_json(url, params={}, api_key=api_key)


def finviz_sector_industry(ticker: str) -> Tuple[str, str]:
    try:
        from pyfinviz.quote import Quote  # type: ignore
        q = Quote(ticker=ticker)
        return (q.sector or "").strip(), (q.industry or "").strip()
    except Exception:
        return "", ""


def upsert_companies_securities(conn, rows: List[Dict[str, Any]]):
    sql_company = f"""
    INSERT INTO {SCHEMA}.companies (composite_figi, name, country, sector, industry)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (composite_figi) DO UPDATE SET
      name=EXCLUDED.name,
      country=COALESCE(EXCLUDED.country, {SCHEMA}.companies.country),
      sector=COALESCE(NULLIF(EXCLUDED.sector,''), {SCHEMA}.companies.sector),
      industry=COALESCE(NULLIF(EXCLUDED.industry,''), {SCHEMA}.companies.industry);
    """

    sql_security_insert = f"""
    INSERT INTO {SCHEMA}.securities (composite_figi, primary_exchange, currency, start_date, end_date, is_active)
    VALUES (%s, %s, %s, NULL, NULL, %s)
    RETURNING security_id;
    """

    sql_security_find = f"""
    SELECT security_id FROM {SCHEMA}.securities
    WHERE composite_figi = %s
    ORDER BY security_id
    LIMIT 1;
    """

    sql_ticker_hist = f"""
    INSERT INTO {SCHEMA}.ticker_history (security_id, ticker, exchange, start_date, end_date, reason)
    VALUES (%s, %s, %s, CURRENT_DATE, NULL, 'bootstrap')
    ON CONFLICT (security_id, ticker, exchange, start_date) DO NOTHING;
    """

    with conn.cursor() as cur:
        execute_batch(
            cur,
            sql_company,
            [(r["composite_figi"], r["name"], r.get("country"), r.get("sector",""), r.get("industry","")) for r in rows],
            page_size=200,
        )

        for r in rows:
            cur.execute(sql_security_find, (r["composite_figi"],))
            found = cur.fetchone()
            if found:
                security_id = found[0]
            else:
                cur.execute(sql_security_insert, (r["composite_figi"], r.get("primary_exchange"), r.get("currency"), r.get("active", True)))
                security_id = cur.fetchone()[0]

            cur.execute(sql_ticker_hist, (security_id, r["ticker"], r.get("primary_exchange") or "UNKNOWN"))

    conn.commit()


def main():
    api_key = getenv("MASSIVE_API_KEY")
    dsn = getenv("PG_DSN")

    print("Loading tickers from CSV...")
    tickers = load_universe_tickers_from_csv()
    print(f"Loaded {len(tickers)} tickers from universe_dev.csv")


    enriched: List[Dict[str, Any]] = []
    for i, t in enumerate(tickers, 1):
        try:
            j = get_ticker_overview(api_key, t)
            res = j.get("results") or {}
            composite_figi = res.get("composite_figi") or ""
            if not composite_figi:
                continue

            mc = res.get("market_cap") or 0
            sector = ""
            industry = ""
            if FINVIZ_ENRICH:
                sector, industry = finviz_sector_industry(t)

            enriched.append({
                "ticker": t,
                "market_cap": float(mc) if mc else 0.0,
                "composite_figi": composite_figi,
                "name": res.get("name") or t,
                "primary_exchange": res.get("primary_exchange") or "",
                "currency": res.get("currency_name") or "",
                "active": bool(res.get("active", True)),
                "sector": sector,
                "industry": industry,
                "country": "US",
            })

            if i % 50 == 0:
                print(f"Processed {i}/{len(tickers)}...")
        except Exception as e:
            print(f"Warn: failed ticker overview for {t}: {e}")

    if not enriched:
        raise RuntimeError("No tickers enriched. Check API key and connectivity.")

    enriched.sort(key=lambda x: x["market_cap"], reverse=True)
    top = enriched[:TOP_N]
    print(f"Selected top {TOP_N} by market cap. Example: {top[0]['ticker']} (${top[0]['market_cap']:.0f})")

    out_json = os.path.join(os.path.dirname(__file__), "top50_tickers.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump([r["ticker"] for r in top], f, indent=2)
    print(f"Wrote {out_json}")

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        upsert_companies_securities(conn, top)
        print("Upserted companies, securities, ticker_history.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
