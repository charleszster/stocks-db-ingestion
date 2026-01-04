# Stocks Research Database

This repository contains the schema, ingestion framework, and identity model for a US-listed equities research database used for discretionary scanning, charting, and systematic analysis.

The project is intentionally developed in phases, each with clearly defined scope and locked semantics.

## Project Structure

/docs/
  phase_2_ingestion.md     — Phase 2: raw market data ingestion (LOCKED)
  phase_3_securities.md   — Phase 3: securities master & identity semantics

## Phase Overview

### Phase 2 — Market Data Ingestion (Complete)
- Raw daily OHLCV prices ingested into `stocks_research.prices_daily`
- Stable runner + job framework
- Massive (Polygon) provider validated
- `prices_daily.security_id` intentionally not FK-enforced
- No identity assumptions beyond basic consistency

### Phase 3 — Securities Master & Identity Semantics (Current)
- Canonical definition of `security_id`
- Company (issuer) metadata including searchable descriptions
- Ticker lifecycle handling (changes, delistings, recycling)
- Support for US-listed Common Stocks and ETFs
- Safe restoration of FK constraints
- Strict separation of provider APIs from canonical database tables

## Design Principles
- Canonical internal identities never depend on vendor-specific identifiers
- All external data providers are isolated behind adapter layers
- Schema correctness and invariants take precedence over ingestion convenience
- Historical correctness is preserved across ticker and vendor changes

This repository is designed for long-term extensibility without refactoring core identity semantics.
