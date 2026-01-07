# src/ingest/jobs/prices_daily.py

from providers.massive.prices_daily import fetch_daily
import sys
import zlib

def run(conn, job_id=None):

    # TEMP Phase-2 bootstrap symbols (you already chose this)
    symbols = ["AAPL", "MSFT", "NVDA"]

    rows_upserted = 0
    api_calls = 0

    for symbol in symbols:
        try:
            bars = fetch_daily(symbol)
        except SystemExit as e:
            sys.exit(1)
        api_calls += 1

        if not bars:
            continue

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO stocks_research.prices_daily (
                    security_id,
                    trade_date,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (
                    %(security_id)s,
                    %(trade_date)s,
                    %(open)s,
                    %(high)s,
                    %(low)s,
                    %(close)s,
                    %(volume)s
                )
                ON CONFLICT (security_id, trade_date) DO NOTHING
                """,
                [
                    {
                        "security_id": zlib.crc32(symbol.encode("utf-8")),   # TEMP Phase-2 mapping
                        "trade_date": bar.trade_date,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                    }
                    for bar in bars
                ],
            )


        rows_upserted += len(bars)

    conn.commit()

    # Return metrics to the runner (Phase-2-friendly)
    return {
        "rows_upserted": rows_upserted,
        "api_calls": api_calls,
    }
