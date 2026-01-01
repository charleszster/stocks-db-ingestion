# Stocks DB — Phase 2: Raw Price & Corporate Action Ingestion

This repository contains **Phase 2** of a multi-stage equity research database:
the ingestion of **raw, unadjusted market data** into PostgreSQL.

This phase is intentionally narrow in scope and opinionated by design.

---

## 🎯 Purpose

The goal of this project is to build a **reproducible, auditable, long-lived**
market data foundation suitable for:

- quantitative equity research
- factor analysis
- historical backtesting
- future machine-learning workflows

This repository is **not** responsible for:
- price adjustments
- indicator calculation
- signal generation
- strategy logic

Those belong in later phases and separate repositories.

---

## 📦 Scope (Phase 2 Only)

### Data Ingested
- Daily OHLCV prices (**unadjusted**)
- Stock splits
- Cash dividends

### Data Source
- Polygon.io (Massive endpoints where applicable)

### Storage
- PostgreSQL (`stocks_research` database)

### Design Rules
- Raw data is preserved as the source of truth
- Ingestion is idempotent (safe to re-run)
- No forward-looking data
- No back-adjustments at ingest time

---

## 🌎 Universe Definition

### Production Universe (Conceptual)
The intended production universe is:

> **All primary-listed U.S. equities**

The production universe is **not** defined by a static file.
Instead, it will eventually be derived dynamically using:
- reference/security metadata
- exchange filters
- liquidity criteria (e.g., dollar volume)
- listing status and effective dates

Those rules will be applied **downstream** via database queries and/or
dedicated universe-construction scripts.

### Development Universe (Practical)
For development, testing, and sanity checks, this repo uses a **small,
static universe** defined in:
config\universe_dev.csv


This file currently contains a limited set of highly liquid stocks and
**does not represent the production universe**.

It exists purely to:
- validate schema correctness
- test ingestion logic
- shorten iteration cycles

---

## 🧱 Repository Structure
stocks-db-ingestion/
├── config/ # Environment and universe configuration
├── scripts/ # Thin entry-point scripts (CLI-style)
├── src/ # Core ingestion logic
├── sql/ # Schema and sanity-check queries
├── tests/ # Unit and integration tests
├── docs/ # Architecture and design notes


### Design Principle
All real logic lives in `src/`.

Scripts in `scripts/` should only:
- parse arguments
- load configuration
- call reusable ingestion functions

---

## ⚙️ Setup

### 1. Database
Create a PostgreSQL database named:
stocks_research


Apply the schema found in:
sql/schema.sql


### 2. Environment Variables
Copy the example file:

```bash
cp .env.example .env

3. Install Dependencies

(Exact tooling TBD — venv/conda/poetry are all acceptable.)

▶️ Running the Ingestion
Prices (Unadjusted)
python scripts/01_ingest_prices.py

Corporate Actions
python scripts/02_ingest_splits.py
python scripts/03_ingest_dividends.py

Sanity Checks
python scripts/99_sanity_checks.py

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


---

## Why this README matters
This does three important things:

1. **Prevents accidental scope creep**
2. **Documents intent, not just mechanics**
3. Makes it crystal clear that:
   - the S&P 500 list was *only a dev tool*
   - the real universe is rule-based and time-aware

---
