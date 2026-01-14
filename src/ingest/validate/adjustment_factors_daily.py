from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ----------------------------
# Small internal reporting model
# ----------------------------

@dataclass
class CheckResult:
    check_id: str
    description: str
    ok: bool
    violations: int
    sample_rows: List[Dict[str, Any]]
    hint: str = ""


class ValidationError(Exception):
    pass


# ----------------------------
# Connection helpers (robust to small framework differences)
# ----------------------------

def _get_conn(ctx: Any):
    """
    Try hard to find a DB-API connection on ctx.

    Expected possibilities (seen in many ingestion frameworks):
      - ctx.conn
      - ctx.db.conn
      - ctx.db.connection
      - ctx.connection
    """
    for attr in ("conn", "connection"):
        if hasattr(ctx, attr):
            return getattr(ctx, attr)

    if hasattr(ctx, "db"):
        db = getattr(ctx, "db")
        for attr in ("conn", "connection"):
            if hasattr(db, attr):
                return getattr(db, attr)

    raise RuntimeError(
        "Could not find a DB connection on ctx. "
        "Expected ctx.conn or ctx.db.conn (or .connection)."
    )


def _fetch_all(conn, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple]:
    params = params or []
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _fetch_val(conn, sql: str, params: Optional[Sequence[Any]] = None) -> Any:
    rows = _fetch_all(conn, sql, params)
    return rows[0][0] if rows else None


def _fetch_dicts(conn, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    params = params or []
    with conn.cursor() as cur:
        cur.execute(sql, params)
        colnames = [d[0] for d in cur.description]
        out = []
        for row in cur.fetchall():
            out.append({colnames[i]: row[i] for i in range(len(colnames))})
        return out


# ----------------------------
# Core validator entrypoint
# ----------------------------

def validate_adjustment_factors_daily(ctx: Any, *, max_samples: int = 20) -> List[CheckResult]:
    """
    Validates Phase 4A adjustment_factors_daily invariants.

    Assumptions:
      - stocks_research.adjustment_factors_daily has columns:
          security_id, trading_date, price_factor
      - stocks_research.prices_daily has:
          security_id, trading_date
      - stocks_research.securities has:
          security_id
    """
    conn = _get_conn(ctx)
    results: List[CheckResult] = []

    def run_check(
        check_id: str,
        description: str,
        count_sql: str,
        sample_sql: str,
        hint: str,
        params: Optional[Sequence[Any]] = None,
    ):
        violations = int(_fetch_val(conn, count_sql, params) or 0)
        sample_rows = []
        if violations > 0:
            sample_rows = _fetch_dicts(conn, sample_sql + f" LIMIT {max_samples}", params)
        results.append(
            CheckResult(
                check_id=check_id,
                description=description,
                ok=(violations == 0),
                violations=violations,
                sample_rows=sample_rows,
                hint=hint,
            )
        )

    # ----------------------------
    # AFD_01: Table exists
    # ----------------------------
    run_check(
        "AFD_01_TABLE_EXISTS",
        "adjustment_factors_daily table exists",
        """
        SELECT CASE WHEN EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='stocks_research'
              AND table_name='adjustment_factors_daily'
        ) THEN 0 ELSE 1 END
        """,
        """
        SELECT 'missing_table' AS problem
        """,
        hint="Run the Phase 4A migrations that create stocks_research.adjustment_factors_daily.",
    )

    # If table missing, stop early (other checks will error).
    if results[-1].ok is False:
        return results

    # ----------------------------
    # AFD_02: No duplicate (security_id, trading_date)
    # ----------------------------
    run_check(
        "AFD_02_NO_DUPLICATES",
        "No duplicate rows for (security_id, trading_date)",
        """
        SELECT COUNT(*) FROM (
            SELECT security_id, trading_date, COUNT(*) AS c
            FROM stocks_research.adjustment_factors_daily
            GROUP BY security_id, trading_date
            HAVING COUNT(*) > 1
        ) t
        """,
        """
        SELECT security_id, trading_date, COUNT(*) AS count_rows
        FROM stocks_research.adjustment_factors_daily
        GROUP BY security_id, trading_date
        HAVING COUNT(*) > 1
        ORDER BY count_rows DESC, security_id, trading_date
        """,
        hint="Enforce uniqueness with a PK/UNIQUE index and ensure your build is idempotent.",
    )

    # ----------------------------
    # AFD_03: FK to securities (no orphan security_id)
    # ----------------------------
    run_check(
        "AFD_03_FK_SECURITIES",
        "All security_id in adjustment_factors_daily exist in securities",
        """
        SELECT COUNT(*)
        FROM stocks_research.adjustment_factors_daily f
        LEFT JOIN stocks_research.securities s
          ON s.security_id = f.security_id
        WHERE s.security_id IS NULL
        """,
        """
        SELECT f.security_id, MIN(f.trading_date) AS first_date, MAX(f.trading_date) AS last_date, COUNT(*) AS rows
        FROM stocks_research.adjustment_factors_daily f
        LEFT JOIN stocks_research.securities s
          ON s.security_id = f.security_id
        WHERE s.security_id IS NULL
        GROUP BY f.security_id
        ORDER BY rows DESC, f.security_id
        """,
        hint="Your builder produced factors for a security_id that is not in the master table. Fix security universe linkage.",
    )

    # ----------------------------
    # AFD_04: Factors only on trading days that exist in prices_daily
    # ----------------------------
    run_check(
        "AFD_04_SUBSET_OF_PRICES",
        "Every (security_id, trading_date) in factors exists in prices_daily",
        """
        SELECT COUNT(*)
        FROM stocks_research.adjustment_factors_daily f
        LEFT JOIN stocks_research.prices_daily p
          ON p.security_id = f.security_id
         AND p.trading_date = f.trading_date
        WHERE p.security_id IS NULL
        """,
        """
        SELECT f.security_id, f.trading_date, f.factor
        FROM stocks_research.adjustment_factors_daily f
        LEFT JOIN stocks_research.prices_daily p
          ON p.security_id = f.security_id
         AND p.trading_date = f.trading_date
        WHERE p.security_id IS NULL
        ORDER BY f.security_id, f.trading_date
        """,
        hint="Your factor generator emitted dates not present in prices_daily (calendar mismatch or off-by-one effective date mapping).",
    )

    # ----------------------------
    # AFD_05: Coverage parity per security (counts match)
    # ----------------------------
    run_check(
        "AFD_05_COVERAGE_PARITY",
        "For each security, factor row count matches prices_daily row count",
        """
        SELECT COUNT(*) FROM (
            SELECT p.security_id
            FROM (
                SELECT security_id, COUNT(*) AS n_prices
                FROM stocks_research.prices_daily
                GROUP BY security_id
            ) p
            LEFT JOIN (
                SELECT security_id, COUNT(*) AS n_factors
                FROM stocks_research.adjustment_factors_daily
                GROUP BY security_id
            ) f
              ON f.security_id = p.security_id
            WHERE COALESCE(f.n_factors, 0) <> p.n_prices
        ) t
        """,
        """
        SELECT
            p.security_id,
            p.n_prices,
            COALESCE(f.n_factors, 0) AS n_factors
        FROM (
            SELECT security_id, COUNT(*) AS n_prices
            FROM stocks_research.prices_daily
            GROUP BY security_id
        ) p
        LEFT JOIN (
            SELECT security_id, COUNT(*) AS n_factors
            FROM stocks_research.adjustment_factors_daily
            GROUP BY security_id
        ) f
          ON f.security_id = p.security_id
        WHERE COALESCE(f.n_factors, 0) <> p.n_prices
        ORDER BY p.security_id
        """,
        hint="Factors must have exactly one row per trading day for every security with prices. Rebuild factors for missing days.",
    )

    # ----------------------------
    # AFD_06: Factor domain (positive and non-null)
    # ----------------------------
    run_check(
        "AFD_06_FACTOR_POSITIVE",
        "factor is non-null and strictly > 0",
        """
        SELECT COUNT(*)
        FROM stocks_research.adjustment_factors_daily
        WHERE price_factor IS NULL OR price_factor <= 0
        """,
        """
        SELECT security_id, trading_date, price_factor
        FROM stocks_research.adjustment_factors_daily
        WHERE price_factor IS NULL OR price_factor <= 0
        ORDER BY security_id, trading_date
        """,
        hint="Factor must be > 0. Null/zero/negative indicates a broken event multiplier (split ratio/dividend math).",
    )

    # ----------------------------
    # AFD_07: Anchor normalization (latest date factor ~= 1.0)
    # ----------------------------
    run_check(
        "AFD_07_ANCHOR_NORMALIZED",
        "Latest trading_date per security has factor = 1.0 (within tolerance)",
        """
        WITH latest AS (
            SELECT security_id, MAX(trading_date) AS max_date
            FROM stocks_research.adjustment_factors_daily
            GROUP BY security_id
        )
        SELECT COUNT(*)
        FROM latest l
        JOIN stocks_research.adjustment_factors_daily f
          ON f.security_id = l.security_id
         AND f.trading_date = l.max_date
        WHERE ABS(f.price_factor - 1.0) > 1e-12
        """,
        """
        WITH latest AS (
            SELECT security_id, MAX(trading_date) AS max_date
            FROM stocks_research.adjustment_factors_daily
            GROUP BY security_id
        )
        SELECT f.security_id, f.trading_date, f.price_factor
        FROM latest l
        JOIN stocks_research.adjustment_factors_daily f
          ON f.security_id = l.security_id
         AND f.trading_date = l.max_date
        WHERE ABS(f.price_factor - 1.0) > 1e-12
        ORDER BY f.security_id
        """,
        hint="If you intend backward-adjusted normalization, latest factor should be exactly 1.0. If you used a different anchor, change this check accordingly.",
    )

    # ----------------------------
    # AFD_08: Piecewise constancy (most days factor should not change)
    # NOTE: This check is heuristic and should be WARN in output if you support it.
    # We'll still report it as a normal check result; your validate runner can treat it as WARN if desired.
    # ----------------------------
    run_check(
        "AFD_08_PIECEWISE_CONSTANT_HEURISTIC",
        "Heuristic: factor changes should be rare (indicates stable behavior between events)",
        """
        WITH deltas AS (
            SELECT
                security_id,
                trading_date,
                price_factor,
                LAG(price_factor) OVER (PARTITION BY security_id ORDER BY trading_date) AS prev_factor
            FROM stocks_research.adjustment_factors_daily
        ),
        changes AS (
            SELECT security_id, trading_date
            FROM deltas
            WHERE prev_factor IS NOT NULL
              AND ABS(price_factor - prev_factor) > 1e-12
        ),
        counts AS (
            SELECT
                (SELECT COUNT(*) FROM changes) AS n_changes,
                (SELECT COUNT(*) FROM stocks_research.adjustment_factors_daily) AS n_total
        )
        SELECT CASE
            WHEN (SELECT n_total FROM counts) = 0 THEN 0
            WHEN (SELECT n_changes FROM counts)::float / (SELECT n_total FROM counts)::float > 0.05 THEN 1
            ELSE 0
        END
        """,
        """
        WITH deltas AS (
            SELECT
                security_id,
                trading_date,
                price_factor,
                LAG(price_factor) OVER (PARTITION BY security_id ORDER BY trading_date) AS prev_factor
            FROM stocks_research.adjustment_factors_daily
        )
        SELECT security_id, trading_date, prev_factor, price_factor
        FROM deltas
        WHERE prev_factor IS NOT NULL
          AND ABS(price_factor - prev_factor) > 1e-12
        ORDER BY security_id, trading_date
        """,
        hint="If >5% of rows change factor, something is likely wrong (double-compounding, date alignment, or float instability). If you have many distributions, loosen threshold.",
    )

    return results


def assert_ok(results: List[CheckResult]) -> None:
    """
    Raises ValidationError if any check failed.
    """
    failed = [r for r in results if not r.ok]
    if failed:
        lines = ["Validation failed:"]
        for r in failed:
            lines.append(f" - {r.check_id}: {r.description} (violations={r.violations})")
        raise ValidationError("\n".join(lines))
