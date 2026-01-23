# BACKUP_AND_RESTORE.md  
**Stock DB Project — Backup & Restore Procedures**

---

## Purpose

This document defines the **authoritative, operational procedures** for backing up
and restoring the `stocks_research` PostgreSQL database.

It is written as a **runbook**, not a design discussion.  
Every command here has been tested in practice.

If followed exactly, these procedures allow you to:
- Recover from corruption or data loss
- Restore known-good historical states
- Proceed with destructive operations safely

---

## Assumptions

- PostgreSQL is installed and running
- Client tools are available on `PATH`:
  - `psql`
  - `pg_dump`
  - `pg_restore`
  - `createdb`
  - `dropdb`
- Connection details are provided via environment variables:
  - `PGHOST`
  - `PGPORT`
  - `PGDATABASE`
  - `PGUSER`
  - `PGPASSWORD`
- Operating system: **Windows**
- Shell: **PowerShell**

---

## Backup Philosophy (Read This Once)

- Backups are **logical** (pg_dump), not filesystem-level
- **Full backups are the source of truth**
- Full backups are **append-only snapshots**
- Schema-only and data-only backups are **supporting artifacts**
- Local disk is the **write target**
- Dropbox is a **secondary mirror**, never the write target

> If something feels scary or uncertain:  
> **Stop and restore from a full backup.**

---

## Backup Locations

### Local (Primary Write Location — gitignored)

stocks-db-ingestion/
└── backups/ ❌ NOT in git
├── schema_only.sql
├── data_only.sql
├── full_20260122_1518.dump
├── full_20260121_2142.dump


Rules:
- `backups/` is local-only
- May be deleted and recreated
- Never committed to Git

Ensure `.gitignore` contains:
/backups/


---

### Dropbox (Secondary / Off-site Mirror)
Dropbox/
└── stocks_db_backups/
├── full/
│ ├── full_20260122_1518.dump
│ ├── full_20260121_2142.dump
├── schema/
│ └── schema_only.sql
├── data/
│ └── data_only.sql


Rules:
- Files are **copied** to Dropbox after creation
- Never write backups directly into Dropbox
- Dropbox is not the source of truth

---

## Backup Types

### 1️⃣ Full Backup (PRIMARY)

- Contains:
  - Schema
  - Data
  - Constraints
  - Indexes
  - Sequences
  - Extensions (including `pgagent`)
- Each file is a **complete snapshot**
- Files are **append-only**
- Timestamped

#### Command (Windows-safe)

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"

pg_dump `
  --format=custom `
  --compress=9 `
  --no-owner `
  --no-privileges `
  -f backups\full_$ts.dump `
  stocks_research

Result:
backups\full_YYYYMMDD_HHMM.dump

2️⃣ Schema-Only Backup (Supporting)
- DDL only
- Used for:
    - Inspection
    - Reference
    - Emergency scaffolding
    - Represents current state
    - Intentionally overwritten

Command:
pg_dump `
  --schema-only `
  --no-owner `
  --no-privileges `
  -f backups\schema_only.sql `
  stocks_research

3️⃣ Data-Only Backup (Supporting)
- Data only
- Plain SQL (uncompressed)
- Used rarely, with caution
- Represents current state
- Intentionally overwritten

Command
pg_dump \`
  --data-only \`
  --disable-triggers \`
  --no-owner \`
  --no-privileges \`
  -f backups\data_only.sql \`
  stocks_research

**Why Full Backups Are Append-Only**
“Append-only” means:
**Existing full backup files are never overwritten.
New backups are added as new files.**

It does **not** mean incremental restore.

Each full backup:
- Is complete
- Is independently restorable
- Requires exactly one file to restore

Old backups are preserved to:
- Guard against silent corruption
- Allow rollback to earlier states
- Support forensic debugging

**Copying Backups to Dropbox**

After a successful local backup:

Full backup:
Copy-Item backups\full_YYYYMMDD_HHMM.dump \`
  "D:\Dropbox\stocks_db_backups\full\"

Schema-only:
Copy-Item backups\schema_only.sql \`
  "D:\Dropbox\stocks_db_backups\schema\"

Data-only
Copy-Item backups\data_only.sql \`
  "D:\Dropbox\stocks_db_backups\data\"

Backup Validation (Required)
Inspect full archive:
pg_restore --list backups\full_YYYYMMDD_HHMM.dump

Expected:
- Schemas
- Tables
- Constraints
- TABLE DATA entries
- No errors

Restore test (Safe, recommended)
Restore into a temporary database:
createdb stocks_research_restore_test

pg_restore `
  --no-owner `
  --no-privileges `
  --dbname=stocks_research_restore_test `
  backups\full_YYYYMMDD_HHMM.dump

Validate:
SELECT COUNT(*) FROM stocks_research.securities;
SELECT COUNT(*) FROM stocks_research.prices_daily;
SELECT COUNT(*) FROM stocks_research.corporate_actions;


Drop test DB:
dropdb stocks_research_restore_test

**Restore Procedures**
Restore Full Backup (Canonical)
dropdb stocks_research
createdb stocks_research

pg_restore `
  --no-owner `
  --no-privileges `
  --dbname=stocks_research `
  backups\full_YYYYMMDD_HHMM.dump

This is the preferred recovery method.

**Restore Schema Only (Cold Rebuild Support)**
dropdb stocks_research
createdb stocks_research

psql stocks_research -f backups\schema_only.sql

Used only when no full backup is available.

**Restore Data Only (Rare, Dangerous)**
psql stocks_research -f backups\data_only.sql

⚠️ Only valid if schema is identical.
If constraints fail → stop immediately.

**Destructive vs Safe Operations**
| Operation                   | Destructive     |
| --------------------------- | --------------- |
| dropdb                      | YES             |
| pg_restore into existing DB | YES             |
| Schema migrations           | YES             |
| Ingestion jobs              | NO (idempotent) |
| Validation queries          | NO              |

When unsure → assume destructive.

**Disaster Scenarios**
| Scenario                | Action                               |
| ----------------------- | ------------------------------------ |
| Bad ingestion run       | Restore last full backup             |
| Failed migration        | Restore pre-migration backup         |
| Partial data corruption | Restore full backup                  |
| Machine loss            | Restore latest backup on new machine |

If uncertain → restore full backup.

Final Notes
- Full backups are the only guaranteed recovery mechanism
- Never trust a backup that hasn’t been inspected
- Never overwrite full backups
- Never patch data manually after corruption

When in doubt:
Restore. Don’t guess.

End of document