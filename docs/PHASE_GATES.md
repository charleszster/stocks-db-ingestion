# Phase Gates & Validation Policy
Repo: stocks-db-ingestion  
Source of truth: src/ingest/validate_runner.py  
Scope: Documentation-only mirror of enforced ingestion gates

This document describes the **exact validation policy enforced by the ingestion system**
before any job is allowed to run.

If this document and `validate_runner.py` ever disagree,  
**`validate_runner.py` is authoritative** and this document must be updated.

---

## Core concept

Each ingestion job is guarded by a **phase gate**.

A phase gate enforces:
1. Required table existence
2. Referential integrity (orphan checks)

Only if all checks pass is the job considered **safe to run**.

---

## Validation dimensions

### 1) `requires_tables`
The job will not run unless **all listed tables exist** in the target schema.

This prevents:
- Partial schema states
- Accidental execution against an uninitialized database
- Silent creation of downstream corruption

---

### 2) `orphan_checks`
The job will not run if **foreign-key-like relationships are violated**, even if
formal FK constraints are absent or deferred.

Each orphan check is defined as:
(source_table, source_column, parent_table)


Meaning:
> Every value in `source_table.source_column` must exist in `parent_table.id`

---

## Job-by-job phase gates

---

### Job: `prices_daily`
**Phase:** Phase 2 — Raw Daily Prices

#### Required tables
- `companies`
- `securities`
- `ticker_history`
- `prices_daily`

#### Orphan checks
- `prices_daily.security_id → securities`

#### Guarantees after validation
- All daily price rows resolve to a canonical security
- No orphan price bars exist
- Identity layer is operational before price ingestion

#### Intentional deferrals
- Corporate actions
- Adjustments
- Fundamentals

---

### Job: `corporate_actions`
**Phase:** Phase 3 — Corporate Actions

#### Required tables
- `companies`
- `securities`
- `ticker_history`
- `corporate_actions`

#### Orphan checks
- `corporate_actions.security_id → securities`

#### Guarantees after validation
- Every corporate action is tied to a canonical security
- Corporate actions cannot introduce identity drift
- Safe foundation for adjustment factor derivation

#### Intentional deferrals
- Adjustment factor computation
- Adjusted price materialization

---

### Job: `adjustment_factors_daily`
**Phase:** Phase 4A — Adjustment Factors

#### Required tables
- `companies`
- `securities`
- `prices_daily`
- `adjustment_factors_daily`

#### Orphan checks
- `adjustment_factors_daily.security_id → securities`

#### Guarantees after validation
- Adjustment factors align with canonical security identity
- Raw prices exist before factor derivation
- Adjusted price views can be safely computed

#### Architectural note
Adjusted prices are intentionally exposed via a **view**, not a physical table.
This prevents drift between raw and adjusted series.

---

### Job: `fundamentals_quarterly_raw`
**Phase:** Phase 4B — Quarterly Fundamentals (Raw)

#### Required tables
- `securities`
- `fundamentals_quarterly_raw`

#### Orphan checks
- *(none enforced at this stage)*

#### Guarantees after validation
- Fundamentals payloads are tied to canonical securities
- Raw vendor data is preserved for auditability and re-derivation
- No dependency on prices or corporate actions

#### Intentional deferrals
- Canonical metric extraction (handled downstream)
- Derived ratios
- Full financial statement normalization

---

## Design implications (important)

### 1) Validation is **structural**, not semantic
The phase gates guarantee:
- Table existence
- Referential integrity

They do **not** guarantee:
- Economic correctness
- Vendor data accuracy
- Completeness of coverage

Those concerns belong to **analysis**, not ingestion safety.

---

### 2) Absence of a gate is intentional
If a relationship is not checked here, that is a *deliberate choice*, not an omission.

Example:
- Fundamentals do not require prices
- Raw fundamentals do not require corporate actions

---

### 3) Phase gates define the trust boundary
If a job passes validation:
- It is safe to run
- It will not structurally corrupt downstream data
- Failures that occur are operational, not architectural

---

## Operational rule (non-negotiable)

> **No ingestion job should ever be run without passing its phase gate.**

If bypassed, the database is no longer in a guaranteed-safe state.

---

## Phase lock status

- Phase 1–4B phase gates are **locked**
- Any change to this file implies:
  - A change to `validate_runner.py`
  - A new phase or explicit architectural decision

---
