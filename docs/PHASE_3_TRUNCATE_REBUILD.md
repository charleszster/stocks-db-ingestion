# Phase 3 — Truncate + Rebuild Checklist (Authoritative)

This checklist performs a clean data reset (rows only, not schema),
applies Phase 3 constraints immediately, and prepares the database
for fresh ingestion with full referential integrity.

No migrations. No validation phases. No drama.

---

## Preconditions (Confirm Before Starting)

- Phase 2 ingestion code is stable and repeatable
- Phase 3 docs are committed and pushed:
  - phase_3_securities.md
  - phase_3_constraints.md
  - phase_3_fk_restoration.md
- No production users or downstream dependencies
- All data currently in the DB is disposable test data

---

## Step 1 — Stop All Writers

Ensure:
- No ingestion jobs are running
- No background scripts are touching the DB
- No interactive sessions are inserting data

This prevents partial writes during reset.

---

## Step 2 — Truncate All Data (Rows Only)

Use TRUNCATE to:
- Remove all rows
- Reset sequences
- Preserve schema and constraints

Recommended order (child → parent):

1) prices_daily
2) ticker_history
3) securities
4) companies
5) provider adapter tables (if present)

If no FKs exist yet, you may use CASCADE safely.

Example intent (conceptual, not literal SQL):
- TRUNCATE prices_daily
- TRUNCATE ticker_history
- TRUNCATE securities
- TRUNCATE companies

After this step:
- All tables are empty
- Identity counters are reset
- No orphans exist by definition

---

## Step 3 — Apply Phase 3 HARD Constraints

Apply all constraints defined in `phase_3_constraints.md`, including:

### companies
- UNIQUE (composite_figi) WHERE NOT NULL

### securities
- PRIMARY KEY (security_id)
- UNIQUE (composite_figi) WHERE NOT NULL
- CHECK (security_type IN ('COMMON_STOCK', 'ETF'))
- CHECK (end_date IS NULL OR end_date >= start_date)

### ticker_history
- CHECK (end_date IS NULL OR end_date >= start_date)
- No overlapping ticker ranges per security
- No overlapping reuse of (exchange, ticker) across securities

### prices_daily
- PRIMARY KEY (security_id, trade_date)
- CHECK (high >= low)
- CHECK (volume >= 0)

At this point:
- Schema enforces all identity invariants
- Invalid data cannot enter the system

---

## Step 4 — Add Foreign Key (Immediately VALID)

Add:

prices_daily.security_id
→ securities.security_id

Because tables are empty:
- FK can be added VALID immediately
- No NOT VALID phase required
- No validation scan required

From this moment on:
- All price data must reference a known security
- Identity correctness is enforced from row #1

---

## Step 5 — (Optional but Recommended) Smoke Test Inserts

Before full ingestion, optionally test:

- Insert one company
- Insert one security
- Insert one ticker_history row
- Insert one prices_daily row

Confirm:
- All inserts succeed
- Invalid inserts fail loudly (e.g., bad security_id)

This confirms constraints are wired correctly.

---

## Step 6 — Resume Phase 2 Ingestion

- Run Phase 2 ingestion normally
- Securities and tickers populate first
- Prices ingest afterward
- Any violation fails immediately and visibly

This is desired behavior.

---

## Step 7 — Post-Rebuild Guarantees

After rebuild:

Guaranteed by the database:
- No orphan price rows
- No ambiguous ticker identity
- No invalid instrument types
- No duplicate daily bars

Guaranteed by process:
- Canonical identity is stable
- Ticker changes are time-ranged
- ETFs are supported without fundamentals
- Finviz and Massive are isolated adapters

---

## What You Do NOT Need Anymore

- Orphan detection
- NOT VALID foreign keys
- FK validation passes
- Migration clean-up logic

Those docs remain as reference for the future.

---

## Phase 3 Status After Completion

- Phase 3 identity model is LIVE
- Referential integrity is enforced
- Database is ready for:
  - Daily discretionary scans
  - Charting across ticker changes
  - Future analytics layers

Phase 3 is COMPLETE at this point.
