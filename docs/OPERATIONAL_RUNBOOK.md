# Operational Runbook — Ingestion System
Repo: stocks-db-ingestion  
Schema: stocks_research  
Audience: Future maintainers, operators, and yourself under pressure

This document describes **how to safely operate the ingestion system**.
It assumes the schema already exists.

---

## Core rule (non-negotiable)

> **Never run an ingestion job without passing its phase gate.**

Validation defines safety.  
Ingestion defines execution.

---

## System components (mental model)

- `run.py` → executes a job
- `validate_runner.py` → decides whether it is safe
- Jobs are isolated; safety is centralized
- Canonical identity is `securities.composite_figi`

---

## Safe execution pattern (always)

For any job:

1. Run validation
2. If validation passes → run ingestion
3. (Optional) Re-run validation to confirm invariants still hold

If validation fails:
- **Stop**
- Fix the structural issue
- Do not “try anyway”

---

## Recommended run order (fresh environment)

### Step 1 — Phase 1: identity
- Migrations only
- No ingestion jobs

---

### Step 2 — Phase 2: raw prices

python -m src.ingest.validate_runner prices_daily
python -m src.ingest.run prices_daily

Guarantees:

Raw daily OHLCV exists

All rows resolve to canonical securities

---

### Step 3 — Phase 3: corporate actions

python -m src.ingest.validate_runner corporate_actions
python -m src.ingest.run corporate_actions


Guarantees:
- Corporate actions are canonicalized
- Adjustment derivation can be trusted

### Step 4 — Phase 4A: adjustment factors
python -m src.ingest.validate_runner adjustment_factors_daily
python -m src.ingest.run adjustment_factors_daily


Guarantees:
Adjustment factors are deterministic
Adjusted prices view is safe to query


### Step 5 — Phase 4B: quarterly fundamentals (raw)
python -m src.ingest.validate_runner fundamentals_quarterly_raw
python -m src.ingest.run fundamentals_quarterly_raw


Guarantees:
Quarterly fundamentals payloads exist
Canonical security identity is respected
Revenue + diluted EPS derivations are reproducible

---

### What reruns are safe?

Safe to re-run anytime:
- prices_daily
- corporate_actions
- adjustment_factors_daily
- fundamentals_quarterly_raw

Assumption:
- Jobs are idempotent as implemented
- Phase gates prevent structural corruption

### What this runbook does NOT cover
- Schema migrations
- Vendor credential rotation
- Performance tuning
- Intraday ingestion
- Analytical modeling

Those are intentionally out of scope.

