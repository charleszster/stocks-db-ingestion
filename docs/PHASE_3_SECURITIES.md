# Phase 3 — Securities Master and Identity Semantics (Schema-First)

## Scope
Phase 3 defines the canonical identity model for US-listed tradable instruments and symbol lifecycle handling.

In scope:
- Canonical `security_id` semantics
- Company metadata (including searchable descriptions)
- Ticker lifecycle (changes, delistings, recycling)
- Support for US Common Stocks and ETFs
- Safe restoration of FK constraints on `prices_daily.security_id`
- Explicit isolation of external data providers (Massive, Finviz)

Out of scope (Phase 3):
- Phase 2 refactors or ingestion changes
- Fundamentals pipelines
- Analytics, scanning, or backtesting logic
- Execution or real-time trading systems

---

## Definitions (Plain English)

- **Company (`companies`)**  
  The business / issuer (e.g., Apple Inc.).

- **Security (`securities`)**  
  A tradable US-listed instrument (e.g., AAPL common stock, SPY ETF).

- **Ticker (`ticker_history`)**  
  A time-ranged trading symbol assigned to a security.

- **Canonical**  
  The single internal source of truth.  
  In this system, `security_id` is canonical.

---

## Canonical Identity Rule (LOCKED)

- `stocks_research.securities.security_id` is the permanent canonical identity for a US-listed tradable instrument.
- Tickers are time-ranged attributes stored only in `stocks_research.ticker_history`.
- `stocks_research.prices_daily` is keyed to `security_id` only.

Implications:
- Ticker changes do not create a new `security_id`.
- Delisting does not delete a security row.
- Ticker recycling must map to a different `security_id` with non-overlapping time ranges.
- Vendor changes never alter canonical identity.

---

## Supported Instrument Types

Phase 3 explicitly supports:
- `COMMON_STOCK`
- `ETF`

Notes:
- ETFs do not require fundamentals.
- Missing fundamentals for ETFs are expected and not errors.
- All supported instruments have prices, volume, and ticker history.

---

## Tables and Semantics

### 1) `stocks_research.companies`
Issuer-level metadata.

Columns:
- composite_figi
- name
- country
- sector
- industry
- description
- description_source
- description_updated_at
- created_at

Semantics:
- Represents the business entity, not a tradable instrument.
- Descriptions are used for text search, classification, and discretionary grouping.
- Sector and industry are sourced from Finviz.

Constraints (conceptual):
- UNIQUE(composite_figi) where composite_figi is not null

---

### 2) `stocks_research.securities`
Canonical instrument identity.

Columns:
- security_id (PK)
- composite_figi
- primary_exchange
- currency
- security_type            -- COMMON_STOCK | ETF
- start_date
- end_date
- is_active

Semantics:
- One row per tradable US instrument.
- `security_id` is permanent.
- Lifecycle dates refer to the instrument, not the ticker.
- `is_active` reflects current tradability, not historical validity.

---

### 3) `stocks_research.ticker_history`
Time-ranged ticker lifecycle.

Columns:
- security_id
- ticker
- exchange
- start_date
- end_date
- reason

Semantics:
- A security may have multiple tickers over time.
- Ticker changes are represented by closing and opening date ranges.
- Ticker recycling is supported and enforced via non-overlapping time windows.

Required invariants:
1) end_date is null OR end_date >= start_date
2) No overlapping ticker ranges for the same security
3) No overlapping reuse of the same (exchange, ticker) across different securities

---

### 4) `stocks_research.prices_daily`
Daily OHLCV facts.

Columns:
- security_id
- trade_date
- open
- high
- low
- close
- volume

Semantics:
- Facts table keyed only to `security_id`.
- Ticker resolution for display is done via `ticker_history`.
- Historical prices remain valid across ticker changes.

---

## External Provider Isolation (Critical Design Rule)

All external data providers are isolated behind adapter layers.

### Massive (Market Data / Reference)
- Provides prices, ticker discovery, ticker events, FIGIs
- Vendor identifiers never appear in canonical tables
- Mapped internally to `security_id`

### Finviz (Classification / Descriptions)
- Source of sector, industry, and company descriptions
- Treated as a replaceable classification provider
- Finviz-specific fields never drive identity

Provider failures must never corrupt or redefine canonical data.

---

## Change Detection Cadence (Conceptual)

Two independent refresh lanes:

1) **Ticker & identity events (daily)**
- Detect ticker changes, renames, delistings
- Update `ticker_history` only

2) **Reference refresh (weekly / monthly)**
- Company descriptions
- Sector / industry classification
- Active status reconciliation

Prices ingestion remains independent and does not mutate identity tables.

---

## FK Restoration Strategy (Conceptual)

Goal:
- Enforce FK from `prices_daily.security_id` to `securities.security_id` safely.

Approach:
1) Add FK as NOT VALID
2) Resolve any orphan identities
3) Validate FK once clean

No Phase 2 ingestion changes are required.

---

## Future Extensions (Explicitly Out of Scope)
- Non-US listings
- Preferred shares, warrants, derivatives
- Real-time execution systems
- Strategy or signal storage
