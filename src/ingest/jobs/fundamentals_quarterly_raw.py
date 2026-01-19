from __future__ import annotations

import os
import time
import json
from typing import Dict, List, Tuple
from datetime import date

import requests

from src.ingest.logging import get_logger

logger = get_logger("fundamentals_quarterly_raw")


# -------------------------
# Environment (LOCKED)
# -------------------------

MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY")
MASSIVE_TIMEOUT_S = int(os.getenv("MASSIVE_TIMEOUT_S", "30"))

TICKERS = [t.strip().upper() for t in os.getenv("TICKERS", "").split(",") if t.strip()]

START_FISCAL_YEAR = int(os.getenv("START_FISCAL_YEAR"))
END_FISCAL_YEAR = int(os.getenv("END_FISCAL_YEAR"))

START_FISCAL_QUARTER = int(os.getenv("START_FISCAL_QUARTER", "1"))
END_FISCAL_QUARTER = int(os.getenv("END_FISCAL_QUARTER", "4"))

if not MASSIVE_API_KEY:
    raise RuntimeError("MASSIVE_API_KEY is required")

if not TICKERS:
    raise RuntimeError("TICKERS must be specified")

BASE_URL = os.getenv("MASSIVE_FINANCIALS_BASE_URL")

ENDPOINTS = {
    "income": os.getenv("MASSIVE_INCOME_STATEMENTS_PATH"),
    "balance": os.getenv("MASSIVE_BALANCE_SHEET_STATEMENTS_PATH"),
    "cashflow": os.getenv("MASSIVE_CASH_FLOW_STATEMENTS_PATH"),
}

if not BASE_URL or not all(ENDPOINTS.values()):
    raise RuntimeError("Massive financial statement endpoints not fully configured in .env")



def massive_get(endpoint: str, ticker: str) -> List[Dict]:
    url = BASE_URL + endpoint
    params = {
        "tickers": ticker,
        "limit": 100,
        "sort": "period_end.asc",
        "apiKey": MASSIVE_API_KEY,
    }

    resp = requests.get(url, params=params, timeout=MASSIVE_TIMEOUT_S)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Massive {endpoint} failed for {ticker}: "
            f"{resp.status_code} {resp.text}"
        )

    payload = resp.json()

    # Massive returns rows under "results"
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise RuntimeError(
            f"Unexpected Massive payload shape for {endpoint}: keys={payload.keys()}"
        )

    return results



# -------------------------
# Normalization
# -------------------------

from datetime import datetime

def fiscal_period_from_row(row: Dict) -> str:
    fy = int(row["fiscal_year"])
    fq = int(row["fiscal_quarter"])
    return f"{fy}Q{fq}"


def quarter_key(row: Dict) -> Tuple[int, int]:
    period_end = row.get("period_end")
    if not period_end:
        raise ValueError("Missing period_end in Massive response")

    d = datetime.strptime(period_end, "%Y-%m-%d").date()
    fy = d.year
    fq = (d.month - 1) // 3 + 1
    return fy, fq



def in_requested_range(fy: int, fq: int) -> bool:
    if fy < START_FISCAL_YEAR or fy > END_FISCAL_YEAR:
        return False
    if fy == START_FISCAL_YEAR and fq < START_FISCAL_QUARTER:
        return False
    if fy == END_FISCAL_YEAR and fq > END_FISCAL_QUARTER:
        return False
    return True


# -------------------------
# DB Helpers
# -------------------------

def resolve_composite_figi(conn, ticker: str) -> str:
    sql = """
        SELECT s.composite_figi
        FROM stocks_research.ticker_history th
        JOIN stocks_research.securities s
          ON s.security_id = th.security_id
        WHERE th.ticker = %s
          AND th.end_date IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql, (ticker,))
        rows = cur.fetchall()

    if len(rows) != 1:
        raise RuntimeError(
            f"{ticker} resolves to {len(rows)} composite_figi values (expected 1)"
        )

    return rows[0][0]


def insert_metrics(
    conn,
    *,
    composite_figi: str,
    fiscal_period: str,
    report_date,
    metrics: Dict[str, float],
    raw_payload: Dict,
):
    sql = """
        INSERT INTO stocks_research.fundamentals_quarterly_raw (
            composite_figi,
            fiscal_period,
            report_date,
            metric_name,
            metric_value,
            source,
            raw_payload
        )
        VALUES (
            %s, %s, %s, %s, %s, 'massive', %s::jsonb
        )
        ON CONFLICT (composite_figi, fiscal_period, metric_name)
        DO UPDATE SET
            metric_value = EXCLUDED.metric_value,
            report_date  = EXCLUDED.report_date,
            raw_payload  = EXCLUDED.raw_payload,
            source       = EXCLUDED.source
    """

    with conn.cursor() as cur:
        for metric_name, metric_value in metrics.items():
            if metric_value is None:
                continue
            cur.execute(
                sql,
                (
                    composite_figi,
                    fiscal_period,
                    report_date,
                    metric_name,
                    metric_value,
                    json.dumps(raw_payload),
                ),
            )


def resolve_security_id(conn, ticker: str) -> int:
    sql = """
        SELECT th.security_id
        FROM stocks_research.ticker_history th
        WHERE th.ticker = %s
          AND th.end_date IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql, (ticker,))
        rows = cur.fetchall()

    if len(rows) != 1:
        raise RuntimeError(
            f"{ticker} resolves to {len(rows)} active security_ids (expected exactly 1)"
        )

    return rows[0][0]


def upsert_row(conn, security_id: int, fy: int, fq: int, payload: Dict):
    sql = """
        INSERT INTO stocks_research.fundamentals_quarterly_raw (
            security_id,
            fiscal_year,
            fiscal_quarter,
            raw_payload,
            as_of_date
        )
        VALUES (
            %s,
            %s,
            %s,
            %s::jsonb,
            CURRENT_DATE
        )
        ON CONFLICT (security_id, fiscal_year, fiscal_quarter)
        DO UPDATE SET
            raw_payload = EXCLUDED.raw_payload,
            as_of_date = EXCLUDED.as_of_date
    """
    with conn.cursor() as cur:
        cur.execute(sql, (security_id, fy, fq, json.dumps(payload)))


# -------------------------
# Job Entry
# -------------------------

def run(conn, job_id: int) -> Dict:
    start = time.time()

    metrics = {
        "job_id": job_id,
        "tickers_total": len(TICKERS),
        "tickers_ok": 0,
        "tickers_failed": 0,
        "rows_upserted": 0,   # runner expects this
        "api_calls": 0,       # runner expects this
        "seconds": 0,
    }

    logger.info(
        f"Starting fundamentals_quarterly_raw | "
        f"FY {START_FISCAL_YEAR}Q{START_FISCAL_QUARTER} "
        f"→ FY {END_FISCAL_YEAR}Q{END_FISCAL_QUARTER}"
    )

    for ticker in TICKERS:
        try:
            logger.info(f"{ticker}: fetching income/balance/cashflow")

            income = massive_get(ENDPOINTS["income"], ticker)
            metrics["api_calls"] += 1

            balance = massive_get(ENDPOINTS["balance"], ticker)
            metrics["api_calls"] += 1

            cashflow = massive_get(ENDPOINTS["cashflow"], ticker)
            metrics["api_calls"] += 1

            # Resolve canonical identity
            composite_figi = resolve_composite_figi(conn, ticker)

            rows_written_for_ticker = 0

            # Phase 4B: use INCOME as the quarter spine
            for row in income:
                fy = row.get("fiscal_year")
                fq = row.get("fiscal_quarter")

                if fy is None or fq is None:
                    continue

                if not in_requested_range(int(fy), int(fq)):
                    continue

                fiscal_period = fiscal_period_from_row(row)
                report_date = row.get("period_end")

                metrics_to_store = {
                    "revenue": row.get("revenue"),
                    "diluted_eps": row.get("diluted_earnings_per_share"),
                }

                insert_metrics(
                    conn,
                    composite_figi=composite_figi,
                    fiscal_period=fiscal_period,
                    report_date=report_date,
                    metrics=metrics_to_store,
                    raw_payload=row,
                )

                rows_written_for_ticker += sum(
                    1 for v in metrics_to_store.values() if v is not None
                )

            conn.commit()

            metrics["rows_upserted"] += rows_written_for_ticker
            metrics["tickers_ok"] += 1

            logger.info(
                f"{ticker}: upserted {rows_written_for_ticker} metric rows"
            )

        except Exception as e:
            conn.rollback()
            metrics["tickers_failed"] += 1
            logger.error(f"{ticker}: FAILED | {e}")

    metrics["seconds"] = round(time.time() - start, 2)
    return metrics