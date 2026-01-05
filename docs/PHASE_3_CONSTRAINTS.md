# Phase 3 — Constraints Package (Authoritative)

This document defines the exact constraints to enforce for Phase 3.
Constraints are grouped by table and classified as:

- HARD: enforced by the database
- PROCESS: guaranteed by ingestion/maintenance logic (not enforced yet)

Apply constraints in the order listed.

---

## 1) stocks_research.companies

### Purpose
Issuer-level business entity metadata.

### HARD constraints
- UNIQUE (composite_figi) WHERE composite_figi IS NOT NULL

Rationale:
- Composite FIGI uniquely identifies an issuer.
- Allows NULL for issuers without FIGI.

### PROCESS guarantees
- Sector and industry values are sourced exclusively from Finviz.
- Description updates overwrite previous values only when changed.
- `description_updated_at` reflects last material change.

---

## 2) stocks_research.securities

### Purpose
Canonical identity for tradable US instruments (Common Stocks and ETFs).

### HARD constraints
- PRIMARY KEY (security_id)
- UNIQUE (composite_figi) WHERE composite_figi IS NOT NULL
- CHECK (end_date IS NULL OR end_date >= start_date)
- CHECK (security_type IN ('COMMON_STOCK', 'ETF'))

Rationale:
- `security_id` is permanent and canonical.
- Composite FIGI must not collide when present.
- Lifecycle dates must be coherent.
- Instrument type must be explicitly known.

### PROCESS guarantees
- Only US-listed instruments are inserted.
- Only Common Stocks and ETFs are allowed.
- No OTC securities are inserted.
- Delisted securities remain in the table with `is_active = false`.

---

## 3) stocks_research.ticker_history

### Purpose
Time-ranged symbol lifecycle for securities.

### HARD constraints
1) Date sanity
   - CHECK (end_date IS NULL OR end_date >= start_date)

2) No overlapping ticker ranges for the same security
   - For a given `security_id`, ticker date ranges must not overlap.

3) No overlapping reuse of the same (exchange, ticker)
   - For a given `(exchange, ticker)`, date ranges must not overlap across different securities.

Rationale:
- Prevents ambiguous symbol identity.
- Supports ticker changes and ticker recycling safely.
- Guarantees a single valid security for any (ticker, exchange, date).

### PROCESS guarantees
- Exactly one “current” ticker exists per security at any time.
- Ticker changes are applied by closing the prior range and opening a new one.
- Historical ticker rows are never mutated except to close `end_date`.

---

## 4) stocks_research.prices_daily

### Purpose
Daily OHLCV facts keyed to canonical identity.

### HARD constraints
- PRIMARY KEY (security_id, trade_date)
- CHECK (high >= low)
- CHECK (volume >= 0)

### FK (added but NOT VALID initially)
- FOREIGN KEY (security_id)
  REFERENCES stocks_research.securities(security_id)
  NOT VALID

Rationale:
- Prevents duplicate daily bars per security.
- Ensures price sanity.
- FK is added without blocking existing data.

### PROCESS guarantees
- Prices are immutable once written.
- Corrections (if any) are applied via controlled backfill jobs.
- Prices ingestion never mutates identity tables.

---

## 5) Cross-table invariants (SYSTEM-WIDE)

These are guarantees that queries may rely on, even if not enforced by SQL yet.

### HARD invariants
- `security_id` uniquely identifies a tradable instrument across all time.
- At most one ticker is valid for a security on any given date.
- At most one security corresponds to a given (ticker, exchange, date).

### PROCESS invariants
- All external provider identifiers are mapped via adapter tables.
- Canonical tables never store provider-specific IDs.
- Provider failures do not redefine identity.

---

## 6) Constraint Application Order (IMPORTANT)

Apply constraints in this order:

1) companies — UNIQUE(composite_figi)
2) securities — PK, CHECKs, UNIQUE(composite_figi)
3) ticker_history — date CHECK
4) ticker_history — non-overlap constraints
5) prices_daily — PK and CHECKs
6) prices_daily — FK to securities (NOT VALID)

Do NOT validate the FK until after orphan analysis.

---

## 7) Explicitly Deferred (NOT Phase 3)

- FK from securities → companies
- Full-text search indexes
- Exchange normalization tables
- Additional security types
- Provider adapter constraints

These are intentionally deferred to avoid premature coupling.
