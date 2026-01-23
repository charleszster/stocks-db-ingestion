# SCHEMA_REBUILD.md  
**Stock DB Project — Schema Rebuild Procedures**

---

## Purpose

This document defines the **authoritative procedures** for rebuilding the
`stocks_research` database schema in worst-case and routine recovery scenarios.

It is intentionally **procedural**, **explicit**, and **destructive-aware**.

If followed exactly, these steps allow the database to be recreated **identically**
from a dead stop.

---

## Assumptions

This document assumes:

- PostgreSQL is **installed and running**
- Client tools (`psql`, `pg_dump`, `pg_restore`, `createdb`, `dropdb`) are on `PATH`
- Connection details are provided via environment variables:
  - `PGHOST`
  - `PGPORT`
  - `PGDATABASE`
  - `PGUSER`
  - `PGPASSWORD`
- The target database **`stocks_research` does not exist**
  - If it exists but is corrupted → drop it first

> This document does **not** cover installing PostgreSQL itself.

---

## Definitions

- **Cold rebuild**  
  Recreate schema from migrations, then repopulate via ingestion.

- **Restore rebuild**  
  Recreate database by restoring from a full backup.

- **Destructive operation**  
  Any action that permanently deletes data (`dropdb`, overwrite restore).

---

## Rebuild Scenarios (Choose One)

### Scenario A — Restore from Full Backup (Preferred)

Use this when:
- Recovering from failure
- Restoring a known-good state
- Time matters more than recomputation

This is the **fastest and safest** path.

---

### Scenario B — Schema + Ingestion Rebuild

Use this when:
- No usable backup exists
- You want a clean recomputation
- Validating ingestion correctness

This is **slower** and **more operationally risky**.

---

## Scenario A — Restore from Full Backup (Primary Path)

### 1. Verify backup exists

dir backups\full_*.dump

Ensure:
File size is non-zero
Filename timestamp matches expectation

### 2. Create empty database
createdb stocks_research

If database already exists:
dropdb stocks_research
createdb stocks_research

⚠️ Destructive — data loss is permanent.

### 3. Restore full backup
pg_restore `
  --no-owner `
  --no-privileges `
  --dbname=stocks_research `
  backups\full_YYYYMMDD_HHMM.dump

Expected:
- No errors
- Informational output only

### 4. Post-restore validation
SELECT COUNT(*) FROM stocks_research.securities;
SELECT COUNT(*) FROM stocks_research.prices_daily;
SELECT COUNT(*) FROM stocks_research.corporate_actions;

Foreign key sanity check:
SELECT COUNT(*)
FROM stocks_research.prices_daily p
LEFT JOIN stocks_research.securities s
  ON p.security_id = s.security_id
WHERE s.security_id IS NULL;

Expected result:
- Row counts > 0
- FK check returns 0

If validation fails → stop and investigate.

### 5. Outcome
At this point:
- Schema is rebuilt
- Data is restored
- Database is trusted

No ingestion is required.

## Scenario B — Schema + Ingestion Rebuild (Secondary Path)

### 1. Create empty database
createdb stocks_research

### 2. Apply schema migrations
Run migrations in version order using the project’s migration process.

This step must:
- Create all schemas
- Create all tables, views, sequences
- Apply constraints and indexes

If a migration fails → stop immediately.

### 3. Verify empty schema
SELECT COUNT(*) FROM stocks_research.securities;

Expected:
- 0 rows
- Table exists

### 4. Run ingestion jobs (ordered)
Jobs must be run in dependency order.

Typical order:
- Securities master
- Ticker history
- Prices (daily)
- Corporate actions
- Adjustment factors
- Fundamentals (raw)
- Fundamentals (derived / YoY)

Each job must be:
- Idempotent
- Logged
- Rerunnable

If a job fails → do not proceed.


### 5. Validation pass
Run validation runners and sanity queries.

Schema rebuild is invalid unless:
- No orphaned rows
- No missing keys
- Views resolve cleanly

## Destructive vs Safe Operations
| Operation                   | Destructive     |
| --------------------------- | --------------- |
| dropdb                      | YES             |
| pg_restore into existing DB | YES             |
| Schema migrations           | YES             |
| Ingestion jobs              | NO (idempotent) |
| SELECT / validation         | NO              |

When unsure → assume destructive.

## Expected Timelines (Approximate)
| Operation           | Time            |
| ------------------- | --------------- |
| Create empty DB     | Seconds         |
| Restore full backup | Seconds–minutes |
| Cold schema rebuild | Minutes         |
| Full ingestion (5y) | Long (hours)    |

## Common Failure Modes

### Restore fails with permission errors
- Check extensions
- Ensure --no-owner --no-privileges used

### Migration fails mid-run
- Drop DB
- Fix migration
- Restart rebuild

### Ingestion partially completes
- Restore last full backup
- Do not manually patch data


## Final Notes
- Backups are the source of truth
- Schema rebuild without backup is a last resort
- Never proceed while “hoping it works”

If the database feels scary to touch:
Stop. Restore from backup.

#### Full backups are append-only snapshots.
#### Each file is complete and independently restorable.
#### Restoring requires exactly one full backup file, never multiple.

### End of document