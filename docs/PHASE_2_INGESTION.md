# Stocks DB - Phase 2: Raw Price & Corporate Action Ingestion

This repository contains Phase 2 of a multi-stage equity research database:
the ingestion of raw, unadjusted market data into PostgreSQL.

This phase is intentionally narrow in scope and opinionated by design.

---

## Relationship to Phase 1

This repository assumes that **Phase 1 (Reference Data & Schema Design)**
has already been completed.

Phase 1 defines:

- The core database schema
- Identifier and entity modeling decisions
- Development universe bootstrapping
- Architectural constraints on ingestion

Phase 2 does not modify these foundations.
It operates strictly within the contracts defined by Phase 1.

---

## Purpose

The goal of this project is to build a reproducible, auditable, long-lived
market data foundation suitable for:

- Quantitative equity research
- Factor analysis
- Historical backtesting
- Future machine-learning workflows

This repository is NOT responsible for:

- Price adjustments
- Indicator calculation
- Signal generation
- Strategy logic

Those belong in later phases and separate repositories.

---

## What "Ingestion" Means in Phase 2

In Phase 2, ingestion refers specifically to:

- Fetching raw, unadjusted market data
- Persisting it exactly as received
- Recording execution metadata and lineage

It does NOT include:

- Price adjustments
- Derived views
- Business logic
- Data interpretation

Those concerns begin in Phase 3.

---

## Scope (Phase 2 Only)

### Data Ingested

- Daily OHLCV prices (unadjusted)
- Stock splits
- Cash dividends

### Data Source

- Massive (formerly Polygon)

### Storage

- PostgreSQL database: stocks_research

### Design Rules

- Raw data is preserved as the source of truth
- Ingestion is idempotent (safe to re-run)
- No forward-looking data
- No back-adjustments at ingest time

---

## Universe Definition

### Production Universe (Conceptual)

The intended production universe is:

- All primary-listed U.S. equities

The production universe is not defined by a static file.
Instead, it will be derived dynamically using:

- Reference / security metadata
- Exchange filters
- Liquidity criteria (e.g. dollar volume)
- Listing status and effective dates

These rules are applied downstream via database queries and/or
dedicated universe-construction scripts.

### Development Universe (Practical)

For development and testing, this repository uses a small static universe:

```
config/universe_dev.csv
```

This file:

- Contains a limited set of highly liquid stocks
- Does NOT represent the production universe

It exists only to:

- Validate schema correctness
- Test ingestion logic
- Shorten iteration cycles

---

## Repository Structure

```
stocks-db-ingestion/
├── config/    Environment and universe configuration
├── scripts/   Thin CLI entry points
├── src/       Core ingestion logic
├── sql/       Schema and sanity-check queries
├── tests/     Unit and integration tests
├── docs/      Architecture and design notes
```

### Design Principle

All real logic lives in src.

Scripts in scripts should only:

- Parse arguments
- Load configuration
- Call reusable ingestion functions

---

## Setup

### 1. Database

Create a PostgreSQL database named:

```
stocks_research
```

Apply the schema in:

```
sql/schema.sql
```

### 2. Environment Variables

Copy the example file:

```
cp .env.example .env
```

Required variables:

- PGHOST
- PGPORT
- PGDATABASE
- PGUSER
- PGPASSWORD

Development port: 5433

### 3. Dependencies

Tooling is intentionally flexible.
venv, conda, or poetry are all acceptable.

---

Phase 2 decision:
stocks_research.prices_daily.security_id is not FK-enforced.
Raw prices are ingested without a securities master.
Referential integrity is restored in Phase 3.

---

## Running the Ingestion (Legacy Scripts)

Prices:

```
python scripts/01_ingest_prices.py
```

Corporate actions:

```
python scripts/02_ingest_splits.py
python scripts/03_ingest_dividends.py
```

Sanity checks:

```
python scripts/99_sanity_checks.py
```

---

## Ingestion Runner

The ingestion runner (python -m ingest.run) is a generic orchestration layer
responsible for:

- Loading configuration
- Opening database connections
- Recording run and job lifecycle metadata
- Executing ingestion jobs
- Capturing success and failure states

The runner contains no provider-specific logic.

---

### Environment Loading

The .env file is loaded explicitly from the project root:

```
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
```

This makes the runner safe to invoke from:

- CLI
- IDEs
- Schedulers
- CI environments

---

### psycopg2 Type Handling

Some Python types require explicit handling.

UUIDs are generated and passed as strings:

```
run_id = str(uuid.uuid4())
job_id = str(uuid.uuid4())
```

JSON parameters must be wrapped:

```
from psycopg2.extras import Json
Json(params)
```

---

### Runner Lifecycle Semantics

- A run represents one invocation of the runner
- A job represents one ingestion task within a run

Rules:

- A run may fail before any jobs start
- Failed runs have status = 'failed' and zero jobs
- Jobs are recorded only if start_job() succeeds
- finish_job() is called only if a job was created

This prevents fabricated job failures.

---

### Verification

PostgreSQL tables:

- ingestion.ingestion_run
- ingestion.ingestion_job

Expected behavior:

- Failed runs may have zero jobs
- Successful runs have one or more successful jobs

---

## What This Repo Does NOT Do

- Adjust prices for splits or dividends
- Smooth or clean data beyond basic validation
- Infer missing values
- Define trading universes
- Generate indicators or signals

These constraints are intentional.

---

## Roadmap

- Phase 3: Adjusted price views
- Phase 4: Factor calculation
- Phase 5: ML feature engineering and training
- Phase 6: Live data and incremental updates

Each phase lives in its own repository.

---

## Philosophy

Raw data should be:

- Boring
- Complete
- Trustworthy

Every transformation must be:

- Explicit
- Versioned
- Reproducible
- Reversible

This repository enforces that contract.

---

## Why This README Exists

- Prevents scope creep
- Documents intent, not just mechanics
- Makes it explicit that:
  - The S&P 500 list was only a dev tool
  - The real universe is rule-based and time-aware

## Phase 2 Status (Complete)

Phase 2 ingests raw, unadjusted daily prices into PostgreSQL.

- Data source: Massive
- Table: stocks_research.prices_daily
- Ingestion is idempotent (ON CONFLICT DO NOTHING)
- security_id FK is intentionally relaxed in Phase 2
- Job execution is auditable via ingestion.ingestion_run / ingestion_job

Phase 3 introduces:
- securities master
- referential integrity
- corporate actions
