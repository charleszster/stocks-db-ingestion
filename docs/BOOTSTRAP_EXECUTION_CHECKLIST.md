# Bootstrap Execution Checklist
Repo: stocks-db-ingestion  
Schema: stocks_research  

Purpose:
Safely bootstrap a fresh database from a dead stop and fully populate it
with canonical market data (Phases 1–4B).

This checklist is meant to be followed sequentially, without improvisation.

---

## Pre-flight (before touching the database)

- [ ] Confirm correct repo and branch
- [ ] Confirm environment variables are set (.env)
- [ ] Confirm database target (host, DB name, schema)
- [ ] Confirm no active ingestion jobs are running
- [ ] Confirm this is a clean bootstrap or an intentional rebuild

If unsure — STOP.

---

## Step 0 — Database creation (external)

Outside this repo:
- Create empty PostgreSQL database
- Ensure role/user permissions are correct

This repo does NOT create databases.

---

## Step 1 — Schema creation

Apply schema-level SQL in this order:

1. Admin / ingestion schema (if applicable)
   - `sql/admin/010_ingestion_schema.sql`

2. Core research schema
   - `sql/stock_research_schema.sql`
   - Any required extensions

Verification:
- [ ] `stocks_research` schema exists
- [ ] Tables exist but are empty

---

## Step 2 — Phase 1: Identity bootstrap

Run:
python scripts/bootstrap/00_bootstrap_universe.py

Creates:
- companies
- securities
- ticker_history

Verification:
- securities populated
- composite_figi populated
- ticker_history non-empty

### Step 3 — Phase 2: Raw daily prices

Validation:
python -m src.ingest.validate_runner prices_daily

Ingestion:
python -m src.ingest.run prices_daily

Verification:
- prices_daily populated
- no orphan security_id values
- expected date range present

### Step 4 — Phase 3: Corporate actions

Validation:
python -m src.ingest.validate_runner corporate_actions

Ingestion:
python -m src.ingest.run corporate_actions

Verification:
- corporate_actions populated
- no orphan security_id values

### Step 5 — Phase 4A: Adjustment factors

Validation:
python -m src.ingest.validate_runner adjustment_factors_daily

Ingestion:
python -m src.ingest.run adjustment_factors_daily

Verification:
- adjustment_factors_daily populated
- adjusted prices view queries correctly


### Step 6 — Phase 4B: Quarterly fundamentals (raw)

Validation:
python -m src.ingest.validate_runner fundamentals_quarterly_raw

Ingestion:
python -m src.ingest.run fundamentals_quarterly_raw

Verification:
- fundamentals_quarterly_raw populated
- revenue and diluted EPS derivable
- no orphan securities


### Step 7 — Post-bootstrap validation

- All validation jobs pass
- Row counts are non-zero and reasonable
- No ingestion errors logged
- Adjusted prices view stable

### Definition of “bootstrap complete”
Bootstrap is complete when:
- All phases 1–4B are populated
- All phase gates pass
- No manual fixes were required
- Database can be dropped and recreated using this checklist

