# Ingestion Dependency Map
Repo: stocks-db-ingestion  
Schema: stocks_research  
Source of truth: validate_runner.py + job layout

This document describes **actual enforced ingestion dependencies**.
If this document and validation logic disagree, validation wins.

---

## Bootstrap (pre-ingestion)
Script:
- `scripts/bootstrap/00_bootstrap_universe.py`

Creates:
- `companies`
- `securities`
- `ticker_history`

Purpose:
- Establish canonical security identity
- Enable all downstream ingestion

Bootstrap is a **one-time operation** per environment.

---

## Canonical dependency (global)

All ingestion jobs ultimately depend on:

- `securities`
- `securities.composite_figi`

Tickers are *attributes*, not identities.

---

## Phase 2 — Raw Daily Prices

Job:
- `prices_daily.py`

Requires:
- `companies`
- `securities`
- `ticker_history`

Writes:
- `prices_daily`

Guarantees:
- All price rows resolve to canonical securities
- No orphan daily bars

Does NOT depend on:
- corporate actions
- adjustment factors
- fundamentals

---

## Phase 3 — Corporate Actions

Job:
- `corporate_actions.py`

Requires:
- `companies`
- `securities`
- `ticker_history`

Writes:
- `corporate_actions`

Guarantees:
- All actions resolve to canonical securities
- Foundation for deterministic adjustments

Does NOT depend on:
- prices
- fundamentals

---

## Phase 4A — Adjustment Factors & Adjusted Prices

Job:
- `adjustment_factors.py`

Requires:
- `companies`
- `securities`
- `prices_daily`

Writes:
- `adjustment_factors_daily`

Consumes:
- corporate action events (Phase 3)

Guarantees:
- Deterministic daily adjustment factors
- Safe adjusted prices view

Depends on:
- Phase 2 (prices)
- Phase 3 (corporate actions)

---

## Phase 4B — Quarterly Fundamentals (Raw)

Job:
- `fundamentals_quarterly_raw.py`

Requires:
- `securities`

Writes:
- `fundamentals_quarterly_raw`

Guarantees:
- Raw quarterly fundamentals are canonicalized
- Revenue and diluted EPS can be derived reproducibly

Explicit non-dependencies:
- prices_daily
- corporate_actions
- adjustment_factors

This independence is **intentional**.

---

## Dependency DAG (conceptual)

Bootstrap
│
▼
securities / ticker_history
│
├──► prices_daily
│
├──► corporate_actions
│
└──► fundamentals_quarterly_raw

prices_daily + corporate_actions
│
└──► adjustment_factors_daily


---

## Design intent (important)

- Dependencies are **minimal by design**
- Absence of a dependency is intentional, not an oversight
- Validation gates enforce safety, not analytics correctness
- Adjusted prices are a view, not a table

---

## Phase lock status

- Phases 1–4B are locked
- This dependency map reflects current enforced behavior

Any change requires:
- validation changes
- documentation updates
- a new phase designation
