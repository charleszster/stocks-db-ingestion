# KNOWN_FAILURE_MODES.md  
**Stock DB Project — Operational Failure Modes & Recovery Actions**

---

## Purpose

This document enumerates **known, realistic failure modes** during bootstrap,
ingestion, and operation of the `stocks_research` database, along with the
**authoritative response** for each.

This is a **panic-prevention document**.

If something goes wrong:
- Do not improvise
- Do not patch data
- Do not continue blindly

Find the scenario below and follow the response exactly.

---

## Guiding Principles

- **Full backups are the source of truth**
- **Restores are cheaper than guesses**
- **Idempotent jobs should not corrupt data**
- **Schema integrity > partial progress**
- When uncertain → **stop and restore**

---

## Failure Modes During Bootstrap

### ❌ Database exists but is misconfigured or corrupted

**Symptoms**
- Missing tables
- Migration failures
- Unexpected constraint errors

**Action**

dropdb stocks_research
createdb stocks_research

Then rebuild using:
- SCHEMA_REBUILD.md
- Restore from full backup if available

### ❌ Schema migration fails mid-run

**Symptoms**
- Migration error
- Partial schema applied

**Action**
- Stop immediately
- Fix migration code
- Drop database
- Restart schema build from scratch

Never attempt to “resume” a failed migration.

---

## Failure Modes During Ingestion


### ❌ Single symbol repeatedly fails (API / data issue)
**Symptoms**
- Repeated retries for same ticker
- Provider returns consistent error

**Action**
- Log symbol as failed
- Continue ingestion
- Do not drop or alter schema
- Do not manually delete rows

Symbols are addressed post-run unless integrity is compromised.

---
### ❌ Ingestion job crashes unexpectedly
**Symptoms**
- Unhandled exception
- Process termination
- Partial inserts

**Action**
- Stop all ingestion
- Assess scope:
    - If job is fully idempotent and rerunnable → re-run job
    - If partial corruption is possible → restore last full backup
- Resume from last completed phase only

When unsure → restore.

---
### ❌ Rate limiting or API throttling
**Symptoms**
- HTTP 429
- Provider backoff signals
- Sudden slowdown

**Action**
- Pause ingestion
- Increase delay / throttle
- Resume when stable

Never bypass rate limits.

---
### ❌ Provider outage or bad data day
**Symptoms**
- Widespread failures
- Inconsistent or obviously wrong data

**Action**
- Stop ingestion
- Restore last full backup
- Resume ingestion on a later date

Do not “push through” bad provider data.

---

## Failure Modes During Phase 6 (5-Year Run)

### ❌ Universe contamination (non-common instruments appear)
**Symptoms**
- Preferreds, warrants, units detected
- Unexpected instrument types in results

**Action**
- Continue first run
- Log affected securities
- Do not delete data mid-run

Resolution occurs **after** first run via deterministic filters.

---
### ❌ Adjustment factors fail validation
**Symptoms**
- Price discontinuities
- Invalid adjusted prices
- Validation failures

**Action**
- Stop immediately
- Restore last full backup
- Fix adjustment logic
- Re-run affected phases

Adjusted data is not patchable.

---

### ❌ Fundamentals missing or inconsistent
**Symptoms**
- Gaps in quarterly data
- Missing YoY calculations

**Action**
- Verify raw fundamentals ingestion
- Verify derivation logic
- Re-run fundamentals phases only

Do not manually insert fundamentals.

---

## Failure Modes After Ingestion

### ❌ Validation fails post-run
**Symptoms**
- FK violations
- Missing rows
- View errors

**Action**
- Stop
- Restore last full backup
- Fix root cause
- Re-run affected phases

A failed validation invalidates the dataset.

---
### ❌ Accidental data modification
**Symptoms**
- Manual UPDATE/DELETE executed
- Untracked schema change

**Action**
- Immediately restore last full backup
- Do not attempt to reverse manually

---
## Failure Modes During Restore
### ❌ Restore fails with permission or ownership errors
**Symptoms**
- Role errors
- Privilege errors

**Action**
- Ensure restore command includes:

    --no-owner --no-privileges

Then retry restore.

---

### ❌ Restore completes but data is missing
**Symptoms**
- Empty tables
- Partial restore

**Action**
- Treat restore as invalid
- Restore from an earlier full backup
- Verify archive with pg_restore --list

---
### Absolute Rules (Non-Negotiable)
- Never manually patch corrupted data
- Never continue after a failed validation
- Never overwrite full backups
- Never assume partial success is acceptable
- Never “just try one more thing” without a restore point

---
### Mental Reset Checklist
If you feel stuck or unsure:
1. Stop all processes
2. Identify last known-good full backup
3. Restore it
4. Re-read:
    - SCHEMA_REBUILD.md
    - BACKUP_AND_RESTORE.md
    - This document
5. Resume calmly

---
## Final Reminder
You are allowed to:
- Stop
- Restore
- Restart

You are **not** allowed to:
- Guess
- Patch
- Hope

The system is designed to survive mistakes — use it.

---
## gEnd of document