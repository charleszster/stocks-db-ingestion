Stocks DB — Phase 2: Raw Price & Corporate Action Ingestion

This repository contains Phase 2 of a multi-stage equity research database:
the ingestion of raw, unadjusted market data into PostgreSQL.

This phase is intentionally narrow in scope and opinionated by design.

🎯 Purpose

The goal of this project is to build a reproducible, auditable, long-lived
market data foundation suitable for:

quantitative equity research

factor analysis

historical backtesting

future machine-learning workflows

This repository is not responsible for:

price adjustments

indicator calculation

signal generation

strategy logic

Those belong in later phases and separate repositories.

📦 Scope (Phase 2 Only)
Data Ingested

Daily OHLCV prices (unadjusted)

Stock splits

Cash dividends

Data Source

Polygon.io (Massive endpoints where applicable)

Storage

PostgreSQL (stocks_research database)

Design Rules

Raw data is preserved as the source of truth

Ingestion is idempotent (safe to re-run)

No forward-looking data

No back-adjustments at ingest time

🌎 Universe Definition
Production Universe (Conceptual)

The intended production universe is:

All primary-listed U.S. equities

The production universe is not defined by a static file.
Instead, it will eventually be derived dynamically using:

reference/security metadata

exchange filters

liquidity criteria (e.g., dollar volume)

listing status and effective dates

Those rules will be applied downstream via database queries and/or
dedicated universe-construction scripts.

Development Universe (Practical)

For development, testing, and sanity checks, this repo uses a small,
static universe defined in:

config/universe_dev.csv


This file currently contains a limited set of highly liquid stocks and
does not represent the production universe.

It exists purely to:

validate schema correctness

test ingestion logic

shorten iteration cycles

🧱 Repository Structure
stocks-db-ingestion/
├── config/   # Environment and universe configuration
├── scripts/  # Thin entry-point scripts (CLI-style)
├── src/      # Core ingestion logic
├── sql/      # Schema and sanity-check queries
├── tests/    # Unit and integration tests
├── docs/     # Architecture and design notes

Design Principle

All real logic lives in src/.

Scripts in scripts/ should only:

parse arguments

load configuration

call reusable ingestion functions

⚙️ Setup
1. Database

Create a PostgreSQL database named:

stocks_research


Apply the schema found in:

sql/schema.sql

2. Environment Variables

Copy the example file:

cp .env.example .env


The project uses standard Postgres environment variables:

PGHOST

PGPORT

PGDATABASE

PGUSER

PGPASSWORD

Current development port: 5433

3. Install Dependencies

Exact tooling is intentionally flexible
(venv, conda, poetry are all acceptable).

▶️ Running the Ingestion (Legacy Scripts)

Prices (Unadjusted):

python scripts/01_ingest_prices.py


Corporate Actions:

python scripts/02_ingest_splits.py
python scripts/03_ingest_dividends.py


Sanity Checks:

python scripts/99_sanity_checks.py

🧠 Ingestion Runner (python -m ingest.run)

The ingestion runner is a generic orchestration layer responsible for:

loading configuration

opening database connections

recording run/job lifecycle metadata

executing ingestion jobs

capturing success and failure states

The runner contains no provider-specific logic and is designed to be reused
across vendors and ingestion tasks.

Environment Loading

The .env file is loaded explicitly from the project root to avoid
current-working-directory–dependent behavior:

from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


This makes the runner safe to invoke from:

CLI

IDEs

schedulers

CI environments

psycopg2 Type Handling

Certain Python types are not adapted automatically by psycopg2 and are handled explicitly:

UUIDs

UUIDs are generated in Python and passed as strings:

run_id = str(uuid.uuid4())
job_id = str(uuid.uuid4())

JSON Parameters

Python dictionaries passed to json/jsonb columns are wrapped explicitly:

from psycopg2.extras import Json
Json(params)

Runner Lifecycle Semantics

A run represents a single invocation of the runner.

A job represents a specific ingestion task executed within a run.

Rules:

A run may fail before any jobs start

Such runs are recorded with status = 'failed'

No job rows are created

Jobs are only recorded if start_job() succeeds

Error handling is defensive:

job_id is initialized before execution

finish_job() is only called if a job was successfully created

This ensures ingestion history reflects real execution behavior without
fabricated failures.

Verification

Execution history can be inspected in Postgres:

Runs: ingestion.ingestion_run

Jobs: ingestion.ingestion_job

Expected behavior:

Failed runs may legitimately have zero jobs

Successful runs will have one or more successful jobs

🔒 What This Repo Does Not Do

Adjust prices for splits or dividends

Smooth or clean data beyond basic validation

Infer missing values

Define trading universes

Generate indicators or signals

These constraints are intentional.

🧭 Roadmap (High Level)

Phase 3: Adjusted price views (derived, reproducible)

Phase 4: Factor calculation

Phase 5: ML feature engineering and training

Phase 6: Live data + incremental updates

Each phase will live in its own repository.

🧠 Philosophy

Raw data should be boring, complete, and trustworthy.

Every transformation should be:

explicit

versioned

reproducible

reversible

This repository exists to enforce that contract.

Why this README matters

This README does three important things:

Prevents accidental scope creep

Documents intent, not just mechanics

Makes it crystal clear that:

the S&P 500 list was only a dev tool

the real universe is rule-based and time-aware