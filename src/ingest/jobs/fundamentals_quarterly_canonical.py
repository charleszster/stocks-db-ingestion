"""
Phase 4B — Canonical Quarterly Fundamentals Rebuild Job

This job rebuilds stocks_research.fundamentals_quarterly_canonical
deterministically from stocks_research.fundamentals_quarterly_raw.

Design principles:
- Derived state only (truncate + rebuild)
- No incremental updates
- No Q4 derivation
- No YoY computation
- No trading-date alignment

Upstream:
- fundamentals_quarterly_raw (append-only)

Downstream:
- Q4 derivation
- YoY growth
- Fundamentals alignment
"""

from src.ingest.db import get_db_connection
from src.ingest.logging import get_logger
from src.ingest.validation import run_sql_assertions

LOGGER = get_logger(__name__)


TRUNCATE_SQL = """
TRUNCATE TABLE stocks_research.fundamentals_quarterly_canonical;
"""


INSERT_CANONICAL_SQL = """
INSERT INTO stocks_research.fundamentals_quarterly_canonical (
    security_id,
    fiscal_year,
    fiscal_quarter,
    report_date,
    revenue,
    eps_diluted,
    source,
    ingestion_run_id
)
SELECT
    s.security_id,

    SUBSTRING(r.fiscal_period, 1, 4)::int AS fiscal_year,
    SUBSTRING(r.fiscal_period, 6, 1)::int AS fiscal_quarter,

    MAX(r.report_date)
        FILTER (WHERE r.metric_name IN ('revenue', 'epsDiluted'))
        AS report_date,

    MAX(r.metric_value)
        FILTER (WHERE r.metric_name = 'revenue')
        AS revenue,

    MAX(r.metric_value)
        FILTER (WHERE r.metric_name = 'epsDiluted')
        AS eps_diluted,

    MAX(r.source) AS source,
    NULL::bigint  AS ingestion_run_id

FROM stocks_research.fundamentals_quarterly_raw r
JOIN stocks_research.securities s
  ON s.composite_figi = r.composite_figi
WHERE r.fiscal_period ~ '^[0-9]{4}Q[1-4]$'
  AND r.metric_name IN ('revenue', 'epsDiluted')
GROUP BY
    s.security_id,
    r.fiscal_period;
"""


# --- Canonical invariants (HARD FAILS) ---------------------------------------

CANONICAL_ASSERTIONS = [
    # one row per security / year / quarter
    """
    SELECT security_id, fiscal_year, fiscal_quarter, COUNT(*) AS n
    FROM stocks_research.fundamentals_quarterly_canonical
    GROUP BY 1,2,3
    HAVING COUNT(*) > 1;
    """,

    # required metrics present
    """
    SELECT *
    FROM stocks_research.fundamentals_quarterly_canonical
    WHERE revenue IS NULL
       OR eps_diluted IS NULL;
    """,

    # valid quarter domain
    """
    SELECT *
    FROM stocks_research.fundamentals_quarterly_canonical
    WHERE fiscal_quarter NOT BETWEEN 1 AND 4;
    """
]


def run():
    """
    Rebuild canonical quarterly fundamentals.
    """
    LOGGER.info(">>> ENTERED fundamentals_quarterly_canonical.run() <<<")

    with get_db_connection() as conn:
        with conn.cursor() as cur:

            LOGGER.info("Truncating canonical quarterly fundamentals...")
            cur.execute(TRUNCATE_SQL)

            LOGGER.info("Inserting canonical quarterly fundamentals...")
            cur.execute(INSERT_CANONICAL_SQL)
            rows_inserted = cur.rowcount

            LOGGER.info("Rows inserted: %s", rows_inserted)

        conn.commit()

    LOGGER.info("Running canonical invariants...")
    run_sql_assertions(
        assertions=CANONICAL_ASSERTIONS,
        job_name="fundamentals_quarterly_canonical"
    )

    LOGGER.info("Canonical quarterly fundamentals rebuild complete.")
