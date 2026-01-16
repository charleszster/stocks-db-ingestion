/*
===============================================================================
Phase 4B — Canonical Quarterly Fundamentals
===============================================================================

Purpose:
--------
Create a canonical, narrow, rebuildable table containing quarterly fundamentals
(revenue and diluted EPS) normalized to one row per:

    (security_id, fiscal_year, fiscal_quarter)

This table is DERIVED STATE.
It is populated exclusively by a deterministic rebuild job and MUST NOT be
manually edited or incrementally patched.

Upstream:
---------
- stocks_research.fundamentals_quarterly_raw (append-only, provider-shaped)

Downstream:
-----------
- Q4 derivation
- YoY growth
- Trading-date alignment
- Feature computation

===============================================================================
*/

BEGIN;

CREATE TABLE IF NOT EXISTS stocks_research.fundamentals_quarterly_canonical (

    -- Identity
    security_id        BIGINT NOT NULL
        REFERENCES stocks_research.securities(security_id),

    fiscal_year        INTEGER NOT NULL,

    fiscal_quarter     INTEGER NOT NULL
        CHECK (fiscal_quarter BETWEEN 1 AND 4),

    -- Dates
    period_end_date    DATE,
    report_date        DATE,

    -- Core metrics (Phase 4B scope)
    revenue            NUMERIC(18,2),
    eps_diluted        NUMERIC(12,4),

    -- Lineage / provenance
    source             TEXT,
    ingestion_run_id   BIGINT,

    -- Q4 and other derived rows will set this TRUE
    is_derived         BOOLEAN NOT NULL DEFAULT FALSE,

    created_at         TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT fundamentals_quarterly_canonical_pk
        PRIMARY KEY (security_id, fiscal_year, fiscal_quarter)
);

COMMENT ON TABLE stocks_research.fundamentals_quarterly_canonical IS
'Canonical quarterly fundamentals (revenue, diluted EPS), one row per security/fiscal year/quarter.
Derived deterministically from fundamentals_quarterly_raw and rebuilt via Phase 4B jobs.';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.security_id IS
'Internal security identifier (FK to securities).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.fiscal_year IS
'Fiscal year of the reporting period (e.g. 2023).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.fiscal_quarter IS
'Fiscal quarter number (1–4). FY rows are excluded from this table.';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.period_end_date IS
'End date of the fiscal reporting period (if available from provider).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.report_date IS
'First public availability date of the quarter’s results (typically filing date).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.revenue IS
'Total revenue for the fiscal quarter.';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.eps_diluted IS
'Diluted earnings per share for the fiscal quarter.';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.source IS
'Source provider for the underlying raw data (e.g. Massive).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.ingestion_run_id IS
'Ingestion run identifier from upstream pipeline (if available).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.is_derived IS
'TRUE for derived rows (e.g. Q4 derived from FY minus Q1–Q3).';

COMMENT ON COLUMN stocks_research.fundamentals_quarterly_canonical.created_at IS
'Row creation timestamp (rebuild time).';

-- Helpful indexes for downstream jobs
CREATE INDEX IF NOT EXISTS idx_fqc_security
    ON stocks_research.fundamentals_quarterly_canonical (security_id);

CREATE INDEX IF NOT EXISTS idx_fqc_fiscal_period
    ON stocks_research.fundamentals_quarterly_canonical (fiscal_year, fiscal_quarter);

COMMIT;
