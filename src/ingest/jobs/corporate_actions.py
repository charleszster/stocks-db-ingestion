from __future__ import annotations

import os
import json
from typing import Any, Dict, List

from ..universe import load_tickers
from ..validate.corporate_actions_events import validate_dividend, validate_split

import psycopg2
from psycopg2.extras import execute_batch, Json

from common import getenv, requests_get_json

BASE_URL = "https://api.massive.com"
SCHEMA = os.getenv("STOCKS_SCHEMA", "stocks_research")

SPLITS_PATH = "/stocks/v1/splits"
DIVIDENDS_PATH = "/stocks/v1/dividends"


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
        invalid = 0

        for s in splits:
            err = validate_split(s)
            if err:
                invalid += 1
                continue

            rows.append((
                sid,
                s["execution_date"],
                s["split_to"],
                s["split_from"],
                s["id"],   # provider_action_id
                Json(s),
            ))

        execute_batch(cur, sql, rows, page_size=2000)

        if invalid:
            print(f"  skipped {invalid} invalid splits for {ticker}")

    conn.commit()
    return len(rows)


def fetch_dividends(api_key: str, ticker: str) -> List[Dict[str, Any]]:
    url = BASE_URL + DIVIDENDS_PATH
    params = {"ticker": ticker, "limit": 5000, "sort": "ex_dividend_date.desc"}
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


def upsert_dividends(conn, ticker: str, dividends: List[Dict[str, Any]]) -> int:
    if not dividends:
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
        %s,           -- security_id
        %s,           -- action_date (ex-dividend date)
        'dividend',   -- action_type
        NULL,         -- value_num
        NULL,         -- value_den
        %s,           -- cash_amount
        %s,           -- currency
        'massive',    -- source
        'massive',    -- provider
        %s,           -- provider_action_id
        %s            -- raw_payload
      )
    ON CONFLICT (provider, provider_action_id) DO UPDATE SET
        security_id = EXCLUDED.security_id,
        action_date = EXCLUDED.action_date,
        cash_amount = EXCLUDED.cash_amount,
        currency    = EXCLUDED.currency,
        source      = EXCLUDED.source,
        raw_payload = EXCLUDED.raw_payload;
    """

    with conn.cursor() as cur:
        sid = security_id_for_ticker(cur, ticker)
        rows = []
        invalid = 0

        for d in dividends:
            err = validate_dividend(d)
            if err:
                invalid += 1
                continue

            rows.append((
                sid,
                d["ex_dividend_date"],
                d["cash_amount"],
                d["currency"],
                d["id"],          # provider_action_id
                Json(d),
            ))

        execute_batch(cur, sql, rows, page_size=2000)

        if invalid:
            print(f"  skipped {invalid} invalid dividends for {ticker}")

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
            n1 = upsert_splits(conn, t, splits)

            dividends = fetch_dividends(api_key, t)
            n2 = upsert_dividends(conn, t, dividends)

            total += n1 + n2
            print(f"{i:>2}/{len(tickers)} {t}: {n1} splits, {n2} dividends inserted/updated")

        print(f"Done. Total splits inserted/updated: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
