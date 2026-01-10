from __future__ import annotations

import os
import json
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import execute_batch, Json

from common import getenv, requests_get_json

BASE_URL = "https://api.massive.com"
SCHEMA = os.getenv("STOCKS_SCHEMA", "stocks_research")

SPLITS_PATH = "/stocks/v1/splits"


def load_tickers() -> List[str]:
    p = os.path.join(os.path.dirname(__file__), "top50_tickers.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


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


def fetch_splits(api_key: str, ticker: str) -> List[Dict[str, Any]]:
    url = BASE_URL + SPLITS_PATH
    params = {"ticker": ticker, "limit": 5000, "sort": "execution_date.desc"}
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


def upsert_splits(conn, ticker: str, splits: List[Dict[str, Any]]) -> int:
    if not splits:
        return 0

    sql = f"""
    INSERT INTO {SCHEMA}.corporate_actions
      (
        security_id,
        action_date,
        action_type,
        value_num,
        value_den,
        cash_amount,
        currency,
        source,
        provider,
        provider_action_id,
        raw_payload
      )
    VALUES
      (
        %s,        -- security_id
        %s,        -- action_date
        'split',   -- action_type
        %s,        -- value_num
        %s,        -- value_den
        NULL,      -- cash_amount
        NULL,      -- currency
        'massive', -- source
        'massive', -- provider
        %s,        -- provider_action_id
        %s         -- raw_payload
      )
    ON CONFLICT (provider, provider_action_id) DO UPDATE SET
        security_id   = EXCLUDED.security_id,
        action_date   = EXCLUDED.action_date,
        value_num     = EXCLUDED.value_num,
        value_den     = EXCLUDED.value_den,
        source        = EXCLUDED.source,
        raw_payload   = EXCLUDED.raw_payload;
    """


    with conn.cursor() as cur:
        sid = security_id_for_ticker(cur, ticker)
        rows = []
        for s in splits:
            dt = s.get("execution_date")
            split_to = s.get("split_to")
            split_from = s.get("split_from")
            if not dt or split_to is None or split_from is None:
                continue
            rows.append((
                sid,
                dt,
                split_to,
                split_from,
                s["id"],   # provider_action_id
                Json(s),
            ))

        execute_batch(cur, sql, rows, page_size=2000)

    conn.commit()
    return len(rows)


def main():
    api_key = getenv("MASSIVE_API_KEY")
    dsn = getenv("PG_DSN")

    tickers = load_tickers()
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        total = 0
        for i, t in enumerate(tickers, 1):
            splits = fetch_splits(api_key, t)
            n = upsert_splits(conn, t, splits)
            total += n
            print(f"{i:>2}/{len(tickers)} {t}: {n} splits inserted/updated")
        print(f"Done. Total splits inserted/updated: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
