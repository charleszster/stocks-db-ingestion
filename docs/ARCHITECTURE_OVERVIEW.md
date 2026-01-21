# Architecture Overview — Stocks DB Ingestion System
Repo: stocks-db-ingestion  
Database: PostgreSQL  
Primary schema: stocks_research  

Status: Phases 1–4B complete, validated, and locked.

---

## Purpose of this document

This document provides a **high-level architectural overview** of the ingestion system.

It answers:
- What this system is
- How data flows end-to-end
- What guarantees exist at each phase
- Where authority lives (code vs documentation)
- How to safely reason about correctness

This is the **entry point** for anyone new to the repo, including future you.

---

## System goal (one sentence)

To ingest, canonicalize, and expose U.S. equity market data in a **deterministic, phase-gated, auditable** manner suitable for long-term research.

---

## Core architectural principles

### 1) Canonical identity first
- The system is built around a single canonical security identity.
- That identity is `securities.composite_figi`.
- Tickers are attributes with history, not identifiers.

If you break this rule, everything downstream becomes unreliable.

---

### 2) Phase-gated ingestion
- Ingestion jobs are not free-running scripts.
- Every job must pass a **phase gate** before execution.
- Phase gates enforce structural safety, not analytics correctness.

Validation defines *whether it is safe to run*.
Ingestion defines *what happens when it runs*.

---

### 3) Minimal, intentional dependencies
- Jobs depend only on what they strictly require.
- Absence of a dependency is deliberate, not an oversight.
- This keeps the system flexible and avoids artificial coupling.

---

### 4) Raw vs derived separation
- Raw vendor data is preserved whenever feasible.
- Derived structures (adjustment factors, adjusted views, normalized metrics) are reproducible.
- No silent overwrites, no irreversible transformations.

---

## High-level data flow

Bootstrap
│
▼
companies ──┐
securities ├──► Canonical identity layer
ticker_hist ┘
│
├──► prices_daily (Phase 2)
│
├──► corporate_actions (Phase 3)
│
└──► fundamentals_quarterly_raw (Phase 4B)

prices_daily + corporate_actions
│
└──► adjustment_factors_daily (Phase 4A)
│
└──► prices_daily_adjusted (VIEW)


All analytical joins are anchored on `security_id`  
External portability uses `composite_figi`.

---

## System components (who does what)

### Ingestion runner
**File:** `src/ingest/run.py`

Responsibilities:
- Job dispatch (job name → ingestion function)
- Execution context (config, DB connection)
- Operational lifecycle (enter/run/exit semantics)

The runner does *not* decide whether a job is safe.

---

### Validation runner
**File:** `src/ingest/validate_runner.py`

Responsibilities:
- Defines phase gates
- Enforces required tables
- Enforces orphan checks
- Decides whether a job is safe to run

This is the **policy authority** for ingestion safety.

---

### Jobs
**Directory:** `src/ingest/jobs/`

Responsibilities:
- Perform one narrowly scoped ingestion task
- Assume validation has already passed
- Do not re-check global invariants

Jobs are intentionally simple and isolated.

---

### Validators
**Directory:** `src/ingest/validate/`

Responsibilities:
- Implement reusable structural checks
- Enforce referential integrity without relying solely on FK constraints
- Support phase gate composition

Validators prevent silent corruption.

---

## Phase summary (guarantees vs deferrals)

### Phase 1 — Core schema & identity
Guarantees:
- Canonical identity exists
- Securities are uniquely identifiable

Defers:
- Prices
- Corporate actions
- Fundamentals

---

### Phase 2 — Raw daily prices
Guarantees:
- Daily OHLCV exists
- No orphan price rows
- Identity is respected

Defers:
- Adjustments
- Fundamentals

---

### Phase 3 — Corporate actions
Guarantees:
- Corporate actions are canonicalized
- Adjustment derivation is possible

Defers:
- Adjustment computation
- Adjusted price materialization

---

### Phase 4A — Adjustment factors
Guarantees:
- Deterministic daily adjustment factors
- Adjusted prices are exposed via a view

Defers:
- Physical adjusted price tables
- Intraday adjustments

---

### Phase 4B — Quarterly fundamentals (raw)
Guarantees:
- Raw fundamentals payloads exist
- Canonical security identity is enforced
- Revenue and diluted EPS can be derived reproducibly

Defers:
- Full financial statements
- TTM metrics
- Advanced ratios

Phase 4B is locked.

---

## What “validated” means in this system

Validated means:
- Required tables exist
- Referential integrity is intact
- No structural corruption will occur if the job runs

Validated does *not* mean:
- Data is economically correct
- Vendor data is complete
- Analytics are sound

Validation enforces **safety**, not **truth**.

---

## Documentation map (how to read this repo)

Start here:
- `ARCHITECTURE_OVERVIEW.md` ← this file

Then:
- `INGESTION_AUDIT.md` — end-to-end design and guarantees
- `PHASE_GATES.md` — exact job safety rules
- `OPERATIONAL_RUNBOOK.md` — how to run this safely
- `dependency_map.md` — enforced DAG
- `PHASE_5_BACKLOG.md` — explicitly deferred work

---

## Trust contract for future maintainers

You may trust this system if:
- You respect phase gates
- You join on canonical identity
- You do not bypass validation
- You treat raw vs derived data correctly

You should not trust:
- Ticker-based joins
- Jobs run without validation
- Assumptions about adjusted data being physically stored

---

## Final note

This ingestion system is designed to be:
- Boring
- Deterministic
- Auditable
- Restartable

If something feels “magical,” it’s probably undocumented — and should be fixed.

Phases 1–4B are complete.
Future work must be additive.

---
