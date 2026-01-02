/* ============================================================
   Ingestion Operations Schema
   ------------------------------------------------------------
   Purpose:
     - Track ingestion runs and jobs
     - Enable resumable, idempotent ingestion
     - Support reproducibility via snapshot tagging
   ============================================================ */

BEGIN;

-- ============================================================
-- 1. Create ingestion schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS ingestion;

COMMENT ON SCHEMA ingestion IS
'Operational schema for ingestion runs, job tracking, checkpoints, and snapshot tagging.';

-- ============================================================
-- 2. ingestion_run
--    One row per ingestion invocation
-- ============================================================

CREATE TABLE ingestion.ingestion_run (
    run_id        UUID PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,

    status        TEXT NOT NULL
        CHECK (status IN ('running', 'success', 'failed', 'partial')),

    git_commit    TEXT NOT NULL,
    git_tag       TEXT,

    invoked_by    TEXT NOT NULL,
    host_name     TEXT NOT NULL,

    notes         TEXT
);

COMMENT ON TABLE ingestion.ingestion_run IS
'Top-level record for each ingestion invocation (manual or automated).';

COMMENT ON COLUMN ingestion.ingestion_run.status IS
'Overall run outcome. partial = some jobs failed.';

COMMENT ON COLUMN ingestion.ingestion_run.git_commit IS
'Git commit hash of the code used for this run.';

-- ============================================================
-- 3. ingestion_job
--    One row per job within a run
-- ============================================================

CREATE TABLE ingestion.ingestion_job (
    job_id          UUID PRIMARY KEY,
    run_id          UUID NOT NULL
        REFERENCES ingestion.ingestion_run (run_id)
        ON DELETE CASCADE,

    job_name        TEXT NOT NULL,
    params_json     JSONB NOT NULL DEFAULT '{}'::jsonb,

    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,

    status          TEXT NOT NULL
        CHECK (status IN ('running', 'success', 'failed')),

    rows_upserted   INTEGER NOT NULL DEFAULT 0,
    rows_deleted    INTEGER NOT NULL DEFAULT 0,
    api_calls       INTEGER NOT NULL DEFAULT 0,
    error_count     INTEGER NOT NULL DEFAULT 0,

    last_checkpoint JSONB,
    error_message   TEXT
);

CREATE INDEX idx_ingestion_job_run
    ON ingestion.ingestion_job (run_id);

CREATE INDEX idx_ingestion_job_name
    ON ingestion.ingestion_job (job_name);

COMMENT ON TABLE ingestion.ingestion_job IS
'Execution record for an individual ingestion job within a run.';

COMMENT ON COLUMN ingestion.ingestion_job.params_json IS
'Job parameters (date ranges, max_workers, universe filters, etc).';

COMMENT ON COLUMN ingestion.ingestion_job.last_checkpoint IS
'Job-level checkpoint for resumability and debugging.';

-- ============================================================
-- 4. symbol_ingestion_state
--    Per-symbol checkpoint and status
-- ============================================================

CREATE TABLE ingestion.symbol_ingestion_state (
    job_name        TEXT NOT NULL,
    symbol          TEXT NOT NULL,

    last_success_at TIMESTAMPTZ,
    checkpoint_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    status          TEXT NOT NULL
        CHECK (status IN ('ok', 'error', 'stale')),

    last_error      TEXT,

    PRIMARY KEY (job_name, symbol)
);

CREATE INDEX idx_symbol_ingestion_state_status
    ON ingestion.symbol_ingestion_state (status);

COMMENT ON TABLE ingestion.symbol_ingestion_state IS
'Per-symbol ingestion checkpoint and status for resumable jobs.';

COMMENT ON COLUMN ingestion.symbol_ingestion_state.checkpoint_json IS
'Symbol-level checkpoint (e.g., last ingested date).';

-- ============================================================
-- 5. snapshot_tag
--    Named snapshot milestones
-- ============================================================

CREATE TABLE ingestion.snapshot_tag (
    snapshot_id UUID PRIMARY KEY,
    tag_name    TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    git_commit  TEXT NOT NULL,
    notes       TEXT
);

COMMENT ON TABLE ingestion.snapshot_tag IS
'Named snapshot milestones tied to a git commit for reproducibility.';

-- ============================================================
-- 6. snapshot_table_stats
--    Per-table stats at snapshot time
-- ============================================================

CREATE TABLE ingestion.snapshot_table_stats (
    snapshot_id UUID NOT NULL
        REFERENCES ingestion.snapshot_tag (snapshot_id)
        ON DELETE CASCADE,

    schema_name TEXT NOT NULL,
    table_name  TEXT NOT NULL,

    row_count   BIGINT NOT NULL,
    min_date    DATE,
    max_date    DATE,

    PRIMARY KEY (snapshot_id, schema_name, table_name)
);

COMMENT ON TABLE ingestion.snapshot_table_stats IS
'Per-table statistics captured at snapshot time.';

COMMIT;
