# BOOTSTRAP_EXECUTION_CHECKLIST.md  
**Stock DB Project — Bootstrap & Operational Hardening**

---

## Purpose

This checklist defines the **authoritative execution sequence** for rebuilding,
validating, and populating the `stocks_research` database from a clean state.

If completed successfully, it proves that the system is:
- Rebuildable
- Recoverable
- Operationally safe
- Ready for large-scale ingestion

This is an **execution checklist**, not a design document.

---

## Preconditions

- PostgreSQL installed and running
- Client tools available on `PATH`:
  - `psql`
  - `pg_dump`
  - `pg_restore`
  - `createdb`
  - `dropdb`
- Python environment available
- Repo cloned locally
- Working directory: repo root
- Postgres connection configured via environment variables:
  - `PGHOST`
  - `PGPORT`
  - `PGDATABASE`
  - `PGUSER`
  - `PGPASSWORD`

---

## Phase 0 — Environment Verification

- [ ] Activate Python environment
- [ ] Verify Python version
- [ ] Install dependencies
  ```powershell
  pip install -r requirements.txt

 - Verify ingestion runner executes
 python -m src.ingest.run --help


## Phase 1 — Database Creation

- Ensure target DB does not exist
 dropdb stocks_research

- Create empty database
createdb stocks_research

- Verify connectivity
psql stocks_research -c "SELECT 1;"


## Phase 2 — Schema Build
- Apply all schema migrations in order
-  Verify schemas exist (ingestion, stocks_research)
-  Verify core tables exist
SELECT COUNT(*) FROM stocks_research.securities;

- Verify views build cleanly
SELECT COUNT(*) FROM stocks_research.prices_daily_adjusted_v;

## Phase 3 — Pre-Ingestion Safety Backup
-  Create backups/ directory (gitignored)
-  Run full backup
$ts = Get-Date -Format "yyyyMMdd_HHmm"
pg_dump `
  --format=custom `
  --compress=9 `
  --no-owner `
  --no-privileges `
  -f backups\full_$ts.dump `
  stocks_research

-  Copy backup to Dropbox
-  Verify archive
pg_restore --list backups\full_$ts.dump

## Phase 4 — Ingestion Dry Runs (Empty DB)
Run each job once, in isolation.
- Securities master
- Ticker history
- Prices (daily)
- Corporate actions
- Adjustment factors
- Fundamentals (raw)
- Fundamentals (derived / YoY)

Rules:
- No uncaught exceptions
- Logging must be clean
- Jobs must be idempotent

## Phase 5 — Validation Pass
-  Run validation runners
-  Verify no orphaned rows
-  Verify foreign key integrity
-  Verify adjustment continuity
-  Verify derived tables populate correctly

Failure here blocks progression.

## Phase 6 — Production Ingestion (5-Year Run)
- Define universe (written, explicit)
- Define start/end dates
- Run prices ingestion (5 years)
- Run corporate actions
- Run adjustment factors
- Run fundamentals
- Run derived metrics

Rules:
- No manual DB edits
- Errors logged, not ignored
- Failed symbols tracked explicitly

## Phase 7 — Post-Ingestion Validation
- Row count sanity checks
- Date coverage verification
- FK and uniqueness checks
- View correctness validation

## Phase 8 — Final Safety Backup
- Run full backup
- Copy to Dropbox
- Verify archive
- Record filename and timestamp

This backup represents the first production-grade dataset.

## Definition of Done
Bootstrap is considered complete when:
- Database can be dropped and rebuilt from scratch
- Full restore works without errors
- Validation passes cleanly
- 5-year dataset is populated and trusted
- System can survive operator error

At this point:
- Tag the repo
- Proceed to research, analytics, or ML work