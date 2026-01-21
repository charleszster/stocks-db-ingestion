# Repo-wide Ingestion Audit (Option C)
Repo: `stocks-db-ingestion`  
Database: PostgreSQL  
Primary schema: `stocks_research`  
Ingestion runner: `src/ingest/run.py` (job → ingestion function)  
Validation runner: `src/ingest/validate_runner.py` (phase gates)  
Canonical security identity: `stocks_research.securities.composite_figi`  
Status: Phase 1–4B complete, validated, and locked (no new ingestion logic implied by this document)

---

## 1) Purpose of this document

This is a repo-wide architectural audit of ingestion, meant to be *trusted* by a future engineer. It defines:

- End-to-end data flow across all phases (1 → 4B)
- What each phase **guarantees** (invariants) vs. what it **intentionally defers**
- The operating model: runners, jobs, validators, schemas
- The contract for canonical identity (`securities.composite_figi`)
- The “phase gates” required to safely run each job

Non-goals:

- No new ingestion logic
- No schema changes
- No “nice to have” refactors
- No retroactive redesign of phase boundaries

---

## 2) System overview (big picture)

At a high level, the repo implements a **deterministic, phase-gated ingestion pipeline** into a single canonical research schema (`stocks_research`).

The system is organized into phases:
- Phase 1 establishes *identity + core tables*.
- Phase 2 ingests *raw daily prices*.
- Phase 3 establishes *canonical security identity* and ingests *corporate actions* needed for adjustments.
- Phase 4A derives *adjustment factors* and provides an *adjusted prices view*.
- Phase 4B ingests *quarterly fundamentals* (raw payload + normalized: revenue, diluted_eps).

The architecture enforces:
- **A single canonical identity** for cross-dataset joins: `securities.composite_figi`
- **Job isolation**: each job has clear inputs, outputs, and invariants
- **Phase gates**: validators prevent running jobs when prerequisites are violated
- **Auditable operations**: run paths are explicit (job runner + validation runner), and invariants are stated

---

## 3) Canonical identity contract: `securities.composite_figi`

### 3.1 Why canonical identity exists
Every dataset in this project (prices, corporate actions, fundamentals) ultimately needs to be joinable without ambiguity. Symbols/tickers are not stable. Vendors disagree. Corporate actions create historical mapping complexity.

Therefore:
- **Canonical identity is NOT the ticker**
- **Canonical identity is `securities.composite_figi`**

### 3.2 What the contract guarantees
If a record is “about a tradable security” in `stocks_research`, it must be able to resolve to exactly one `security_id`, whose stable public identifier is `composite_figi`.

This implies:
- Tickers are treated as *attributes with history*.
- Downstream tables join via `security_id` (internal PK), and can expose `composite_figi` for portability.

### 3.3 What is intentionally deferred
This contract does not imply:
- Perfect global security master coverage
- A full-blown entity resolution system across all exchanges and asset classes
- Intraday identifiers, options identifiers, or complex corporate hierarchy mapping
- Multi-vendor reconciliation beyond the chosen provider strategy

---

## 4) Runners, jobs, validators, and schemas

### 4.1 Key concepts

**Runner (`src/ingest/run.py`)**
- The executable entrypoint for ingestion.
- Accepts a job name (string) and dispatches to the correct ingestion function.
- Owns operational concerns: configuration loading, DB context, job lifecycle semantics (e.g., “entered job”, “success/failure”, etc. as implemented).

**Job**
- A single ingestion unit with a narrowly-defined scope and explicit dependencies.
- Examples by phase: “prices_daily”, “corporate_actions”, “adjustment_factors”, “fundamentals_quarterly”, etc.

**Validator(s)**
- Pre-flight checks that assert phase invariants.
- Must run before ingestion to avoid corrupting or partially-populating dependent tables.
- Validators act as “phase gates”: a job is *only safe to run* when its gate passes.

**Validation runner (`src/ingest/validate_runner.py`)**
- Orchestrates which validators apply to which job.
- Encodes the dependency graph as *policy* (“these invariants must hold before you run X”).

**Schemas**
- `stocks_research`: canonical analytical schema (the source of truth for research queries)
- (If present) `ingestion`: operational metadata about ingestion runs/checkpoints/snapshots/etc.
  - This document treats operational schema as a support system, not the analytical truth.

### 4.2 The operating model: deterministic + gated
The system is designed to be:
- Deterministic: reruns should converge (upserts / idempotent patterns as implemented)
- Gated: validators prevent “run-it-anyway” mistakes
- Auditable: it’s always clear which job ran and whether it was allowed to run

This implies the repo is closer to a “data product” than a one-off script bundle.

---

## 5) Phase-by-phase audit

### Phase 1 — Core schema & identity tables

**Purpose**
- Establish the canonical schema foundation: companies, securities, ticker history, and related identity entities.

**Primary outputs**
- `stocks_research.companies`
- `stocks_research.securities`
- `stocks_research.ticker_history`
- Any other identity/support tables created in Phase 1 migrations

**Key invariants (guarantees)**
- `securities` exists and contains a stable identifier: `composite_figi`
- Basic identity tables exist and are internally consistent
- There is a defined mechanism to map tickers to a canonical security over time (ticker history concept)

**Intentional deferrals**
- Perfect entity resolution across all vendors
- Full coverage of all security types
- Corporate actions and adjustment correctness (not Phase 1’s job)
- Fundamentals (not Phase 1’s job)

---

### Phase 2 — Raw daily prices ingestion

**Purpose**
- Ingest daily OHLCV price bars into `stocks_research` for a defined symbol/security universe.

**Primary outputs**
- `stocks_research.prices_daily` (raw daily bars)

**Inputs / dependencies**
- Phase 1 identity tables exist
- Active tickers resolve deterministically to a security (directly or via mapping rules in code)

**Key invariants (guarantees)**
- No orphan price rows: every price row resolves to a valid `security_id`
- A known ingestion window exists (e.g., “last 5 years of daily” or whatever is configured)
- The table is safe to rerun without creating duplicates (idempotent semantics as implemented)

**Intentional deferrals**
- Split/dividend adjustments (handled later)
- Adjusted price series as a stored table (Phase 4A provides a view-based approach)
- Intraday prices (explicitly out of scope unless a future phase adds them)

---

### Phase 3 — Canonical securities + corporate actions

**Purpose**
- Lock in canonical security identity as the join backbone.
- Ingest corporate actions required for adjustments (splits + dividends at minimum).

**Primary outputs**
- Canonical `stocks_research.securities` population (or enrichment)
- Corporate action tables (e.g., `dividends`, `splits`, or a unified `adjustment_events` pattern depending on the repo’s design)

**Inputs / dependencies**
- Phase 1 identity exists
- Phase 2 prices can exist independently, but Phase 3 enables correctness for “adjusted” analytics

**Key invariants (guarantees)**
- Canonical identity is operational: `security_id` ↔ `composite_figi` is stable and usable
- Corporate actions are persisted in a normalized structure that can drive deterministic factor derivation

**Intentional deferrals**
- Computing adjusted bars (Phase 4A)
- Complex corporate actions beyond the adjustment set (mergers/spinoffs/etc unless explicitly included)
- Cross-vendor reconciliation of corporate actions beyond a chosen source-of-truth policy

---

### Phase 4A — Adjustment factors & adjusted prices view

**Purpose**
- Derive deterministic adjustment factors from corporate actions.
- Provide an adjusted daily prices interface without duplicating raw bars.

**Primary outputs**
- `stocks_research.adjustment_factors_daily` (or equivalent daily factor table)
- `stocks_research.prices_daily_adjusted` view (or equivalent)

**Inputs / dependencies**
- Phase 2 raw prices
- Phase 3 corporate actions

**Key invariants (guarantees)**
- Adjustment factors are deterministic and reproducible given the same input events
- The adjusted prices interface is a *view* over raw bars + factors (ensures no drift via duplicated storage)
- Joins remain stable because factors and prices share `security_id`

**Intentional deferrals**
- Storing adjusted bars as a physical table (view chosen intentionally)
- Intraday adjustments (only daily scope is guaranteed)
- “Total return” series or benchmark series unless explicitly defined

---

### Phase 4B — Quarterly fundamentals ingestion (LOCKED)

**Purpose**
- Ingest quarterly fundamentals into `stocks_research` with both:
  - raw vendor payload storage (for auditability)
  - a normalized subset: **revenue** and **diluted_eps** (YoY extraction policy as designed)

**Primary outputs**
- Fundamentals raw payload table(s)
- A normalized quarterly fundamentals table keyed by `security_id` and period end (or equivalent)
- Only revenue and diluted EPS are treated as first-class normalized metrics in Phase 4B

**Inputs / dependencies**
- Canonical security identity must be stable (Phase 3)
- Vendor payload parsing must be deterministic

**Key invariants (guarantees)**
- Fundamentals are keyed to canonical `security_id`
- The chosen normalized fields are:
  - revenue
  - diluted_eps
- The raw payload exists to permit future re-derivation and debugging
- Phase 4B is validated and locked: reruns are safe under the existing idempotency strategy

**Intentional deferrals**
- Full financial statements (income/balance/cashflow line items)
- TTM derivations unless already included by policy (Phase 4B’s statement says “revenue, diluted_eps only”)
- Advanced derived metrics (margins, ROIC, accruals, etc.)
- Full “tall schema” for line items (explicitly deferred; see backlog note)

---

## 6) End-to-end data flow (lineage)

### 6.1 Lineage narrative
1) **Identity foundation (Phase 1)**  
   Creates the entities required to attach any fact table (prices/fundamentals/actions) to a canonical security.

2) **Raw daily prices (Phase 2)**  
   Loads market observations keyed to `security_id`.

3) **Corporate actions + canonical mapping maturity (Phase 3)**  
   Loads the events required to translate raw prices into adjusted series.

4) **Adjustment factors + adjusted view (Phase 4A)**  
   Derives daily adjustment factors and exposes adjusted prices via view (no duplicate storage).

5) **Quarterly fundamentals (Phase 4B)**  
   Loads quarterly accounting observations keyed to `security_id`, storing raw payload + normalized revenue/diluted EPS.

### 6.2 Join backbone
All downstream analytics should join on:

- Fact tables (prices, fundamentals, factors, events) → `security_id`
- Canonical external identifier for interchange/debugging → `securities.composite_figi`

Tickers are not a join key; they are an attribute and may be used for user-facing labeling only.

---

## 7) What “validated” means here

Validation is not vague optimism. In this repo, “validated” means:

- The job’s prerequisite tables exist
- The identity mapping preconditions hold (no ambiguity where uniqueness is required)
- There are no orphan facts violating foreign keys or assumed identity rules
- Basic sanity checks are satisfied (rowcounts > 0, expected coverage, etc. as implemented)
- The job is declared safe-to-run by the validation runner

The **validation runner** is the source of truth for phase gates:
- If `validate_runner.py` blocks a job, running it anyway is treated as unsafe.

---

## 8) Operational runbook (how to run this safely)

### 8.1 Golden rule: validate before ingest
The intended operational flow is:

1) Run validation for the job (phase gate)  
2) If safe, run ingestion for the job  
3) Re-run validation (optional but recommended) to confirm invariants still hold after a run

### 8.2 What the runners enforce (by role)

- `src/ingest/validate_runner.py` enforces *policy*:
  - prerequisites and invariants
  - “safe to run” decision

- `src/ingest/run.py` enforces *execution*:
  - dispatch: job → ingestion function
  - environment loading and DB connection context
  - job lifecycle semantics (logging/tracking as implemented)

---

## 9) Phase guarantees vs. deferred backlog (explicit)

### Guaranteed by end of Phase 4B
- Canonical identity exists and is stable: `securities.composite_figi`
- Daily raw prices exist (Phase 2)
- Corporate actions exist (Phase 3)
- Daily adjustment factors exist + adjusted prices are exposed via view (Phase 4A)
- Quarterly fundamentals exist (raw payload + normalized: revenue, diluted_eps) (Phase 4B)

### Explicit deferrals (NOT bugs)
- Intraday price ingestion
- Full financial statement line items (tall schema)
- Broad derived metrics layer (margins, ROIC, etc.)
- Multi-vendor reconciliation engine
- Complex corporate action types beyond the adjustment set

---

## 10) Trust model: how a future engineer should reason about correctness

A future engineer should trust this system if:
- They respect the phase gates
- They treat `composite_figi` as canonical identity
- They avoid using tickers as stable join keys
- They understand the “raw vs derived” split:
  - raw facts (prices/fundamentals payload) are preserved
  - derived structures (factors, adjusted view) are reproducible

And they should *not* trust:
- Any ad hoc query that joins on ticker without using the security mapping
- Any ingestion run executed without the validator’s approval
- Any result that assumes adjusted data exists as a physical table (it’s a view by design)

---

## 11) Known sharp edges (design realities)

These are not necessarily “problems,” but they are places where engineers should slow down:

- Corporate actions are historically messy; adjustments are only as correct as the event feed + mapping.
- Identity and ticker history must be treated as first-class — otherwise joins drift silently.
- Fundamentals vendors revise history; raw payload storage exists to re-derive when needed.
- A view-based adjusted series prevents drift, but may require indexing strategy awareness on the underlying tables for performance.

---

## 12) Appendix: recommended diagrams (documentation-only)

(Not required for correctness, but ideal for trust.)

1) **Entity flow diagram**
- securities ↔ ticker_history
- prices_daily → (join) adjustment_factors_daily → prices_daily_adjusted (view)
- fundamentals_quarterly → securities

2) **Phase dependency graph**
- P1 → P2
- P1 → P3
- P2 + P3 → P4A
- P3 → P4B

3) **Operational sequence**
- validate(job) → run(job) → validate(job)

---

## 13) Versioning / “locked” meaning

When a phase is marked “locked,” it means:
- The schema and invariants are stable
- The ingestion logic for that phase should not change without a new phase or explicit mandate
- Documentation describes the behavior as a contract

Phase 4B is locked.

---
