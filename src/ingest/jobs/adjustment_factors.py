# src/ingest/jobs/adjustment_factors.py

from datetime import datetime, time
from decimal import Decimal
import logging

from src.ingest.jobs.prices_daily import run as run_prices_daily


logger = logging.getLogger(__name__)
DERIVATION_VERSION = "v1"


def run(conn, job_id):

    """
    Phase 4A — Adjustment Factors (Daily)

    Deterministic, truncate-and-rebuild derivation of:
      - stocks_research.adjustment_events
      - stocks_research.adjustment_factors_daily

    Uses:
      - stocks_research.corporate_actions
      - stocks_research.prices_daily

    Raw prices and corporate actions are NEVER mutated.
    """

    conn.autocommit = False

    try:
        with conn.cursor() as cur:

            # --------------------------------------------------------------
            # Step 1: Ensure prices_daily exists (auto-heal)
            # --------------------------------------------------------------
            cur.execute("""
                SELECT MAX(trade_date)
                FROM stocks_research.prices_daily
            """)
            max_price_date = cur.fetchone()[0]

            if max_price_date is None:
                logger.info("prices_daily empty; running prices ingestion")
                run_prices_daily()
                conn.commit()

                cur.execute("""
                    SELECT MAX(trade_date)
                    FROM stocks_research.prices_daily
                """)
                max_price_date = cur.fetchone()[0]

                if max_price_date is None:
                    raise RuntimeError("prices_daily still empty after ingestion")

            logger.info("Anchor will be based on latest trade_date=%s", max_price_date)

            # --------------------------------------------------------------
            # Step 2: Truncate derived tables
            # --------------------------------------------------------------
            cur.execute("TRUNCATE stocks_research.adjustment_events")
            cur.execute("TRUNCATE stocks_research.adjustment_factors_daily")

            # --------------------------------------------------------------
            # Step 3: Build adjustment_events
            # --------------------------------------------------------------
            cur.execute("""
                SELECT
                    ca.provider,
                    ca.provider_action_id,
                    ca.security_id,
                    ca.action_type,
                    ca.action_date,
                    ca.value_num,
                    ca.value_den,
                    ca.cash_amount
                FROM stocks_research.corporate_actions ca
                ORDER BY ca.security_id, ca.action_date
            """)

            rows = cur.fetchall()
            logger.info("Processing %d corporate actions", len(rows))

            event_rows = []

            for (
                provider,
                provider_action_id,
                security_id,
                action_type,
                action_date,
                value_num,
                value_den,
                cash_amount
            ) in rows:

                effective_ts = datetime.combine(action_date, time(0, 0))

                split_mult = Decimal("1")
                dividend_mult = Decimal("1")
                prev_close = None
                prev_close_date = None
                status = "RESOLVED"

                if action_type == "SPLIT":
                    if value_num is not None and value_den is not None:
                        # value_num / value_den = new / old
                        # price multiplier = old / new
                        split_mult = Decimal(value_den) / Decimal(value_num)

                elif action_type == "DIVIDEND":
                    cur.execute("""
                        SELECT trade_date, close
                        FROM stocks_research.prices_daily
                        WHERE security_id = %s
                          AND trade_date < %s
                        ORDER BY trade_date DESC
                        LIMIT 1
                    """, (security_id, action_date))

                    row = cur.fetchone()

                    if row is None:
                        status = "MISSING_PREV_CLOSE"
                    else:
                        prev_close_date, prev_close = row
                        prev_close = Decimal(prev_close)

                        if prev_close <= 0 or cash_amount is None:
                            status = "BAD_PREV_CLOSE"
                        else:
                            dividend_mult = (
                                (prev_close - Decimal(cash_amount)) / prev_close
                            )

                price_mult = split_mult * dividend_mult

                event_rows.append((
                    security_id,
                    provider,
                    provider_action_id,
                    action_type,
                    effective_ts,
                    split_mult,
                    dividend_mult,
                    price_mult,
                    prev_close_date,
                    prev_close,
                    status,
                    DERIVATION_VERSION
                ))

            cur.executemany("""
                INSERT INTO stocks_research.adjustment_events (
                    security_id,
                    provider,
                    provider_action_id,
                    action_type,
                    effective_ts,
                    split_price_mult,
                    dividend_price_mult,
                    price_mult,
                    prev_close_date,
                    prev_close,
                    resolution_status,
                    derivation_version
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, event_rows)

            logger.info("Inserted %d adjustment_events", len(event_rows))

            # --------------------------------------------------------------
            # Step 4: Build adjustment_factors_daily
            # --------------------------------------------------------------
            cur.execute("""
                SELECT DISTINCT security_id
                FROM stocks_research.prices_daily
                ORDER BY security_id
            """)

            security_ids = [r[0] for r in cur.fetchall()]

            for security_id in security_ids:

                cur.execute("""
                    SELECT trade_date
                    FROM stocks_research.prices_daily
                    WHERE security_id = %s
                    ORDER BY trade_date DESC
                """, (security_id,))

                trade_dates = [r[0] for r in cur.fetchall()]
                anchor_date = trade_dates[0]

                cur.execute("""
                    SELECT
                        effective_ts,
                        split_price_mult,
                        dividend_price_mult
                    FROM stocks_research.adjustment_events
                    WHERE security_id = %s
                    ORDER BY effective_ts DESC
                """, (security_id,))

                events = cur.fetchall()
                event_idx = 0

                split_factor = Decimal("1")
                dividend_factor = Decimal("1")
                volume_factor = Decimal("1")

                for trade_date in trade_dates:
                    while (
                        event_idx < len(events) 
                        and events[event_idx][0].date() > trade_date):

                        split_mult = Decimal(events[event_idx][1])
                        dividend_mult = Decimal(events[event_idx][2])

                        split_factor *= split_mult
                        dividend_factor *= dividend_mult
                        volume_factor *= (Decimal("1") / split_mult)

                        event_idx += 1

                    cur.execute("""
                        INSERT INTO stocks_research.adjustment_factors_daily (
                            security_id,
                            trade_date,
                            split_factor,
                            dividend_factor,
                            volume_factor,
                            anchor_date,
                            derivation_version,
                            derived_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,now())
                    """, (
                        security_id,
                        trade_date,
                        split_factor,
                        dividend_factor,
                        volume_factor,
                        anchor_date,
                        DERIVATION_VERSION
                    ))

            conn.commit()
            logger.info("Adjustment factors derivation complete")
            return {
                "rows_upserted": len(event_rows),
            }

    except Exception:
        conn.rollback()
        raise
