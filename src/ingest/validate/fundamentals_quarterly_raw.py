"""
Phase 4B Validator — fundamentals_quarterly_raw

Asserts structural correctness of quarterly fundamentals ingestion.

Invariants enforced:
1. No duplicate (composite_figi, fiscal_period, metric_name)
2. Exactly one revenue per (composite_figi, fiscal_period)
3. Exactly one diluted_eps per (composite_figi, fiscal_period)
"""

# NOTE: This validator must be run via:
# python -m src.ingest.validate fundamentals_quarterly_raw

from src.ingest.validate_base import (
    ValidationResult,
    run_sql_check,
)


def validate_fundamentals_quarterly_raw(conn) -> ValidationResult:
    results = []

    # ------------------------------------------------------------------
    # Check 1: No duplicate rows
    # ------------------------------------------------------------------
    results.append(
        run_sql_check(
            conn,
            name="no duplicate (composite_figi, fiscal_period, metric_name)",
            sql="""
                SELECT COUNT(*) FROM (
                    SELECT
                        composite_figi,
                        fiscal_period,
                        metric_name
                    FROM stocks_research.fundamentals_quarterly_raw
                    GROUP BY
                        composite_figi,
                        fiscal_period,
                        metric_name
                    HAVING COUNT(*) > 1
                ) t;
            """,
            expect_zero=True,
        )
    )

    # ------------------------------------------------------------------
    # Check 2: Missing required metrics
    # ------------------------------------------------------------------
    results.append(
        run_sql_check(
            conn,
            name="exactly one revenue and one diluted_eps per quarter",
            sql="""
                WITH quarters AS (
                    SELECT DISTINCT
                        composite_figi,
                        fiscal_period
                    FROM stocks_research.fundamentals_quarterly_raw
                ),
                metrics AS (
                    SELECT
                        composite_figi,
                        fiscal_period,
                        metric_name
                    FROM stocks_research.fundamentals_quarterly_raw
                    WHERE metric_name IN ('revenue', 'diluted_eps')
                )
                SELECT COUNT(*) FROM (
                    SELECT
                        q.composite_figi,
                        q.fiscal_period
                    FROM quarters q
                    LEFT JOIN metrics m
                      ON q.composite_figi = m.composite_figi
                     AND q.fiscal_period = m.fiscal_period
                    GROUP BY
                        q.composite_figi,
                        q.fiscal_period
                    HAVING COUNT(m.metric_name) <> 2
                ) t;
            """,
            expect_zero=True,
        )
    )

    # ------------------------------------------------------------------
    # Check 3: Metric cardinality sanity
    # ------------------------------------------------------------------
    results.append(
        run_sql_check(
            conn,
            name="required metrics have valid cardinality",
            sql="""
                SELECT COUNT(*) FROM (
                    SELECT
                        composite_figi,
                        fiscal_period,
                        metric_name
                    FROM stocks_research.fundamentals_quarterly_raw
                    WHERE metric_name IN ('revenue', 'diluted_eps')
                    GROUP BY
                        composite_figi,
                        fiscal_period,
                        metric_name
                    HAVING COUNT(*) <> 1
                ) t;
            """,
            expect_zero=True,
        )
    )

    return ValidationResult.combine(results)
