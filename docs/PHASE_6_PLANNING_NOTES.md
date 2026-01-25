# PHASE_6_PLANNING_NOTES.md  
**Stock DB Project — 5-Year Ingestion Planning (Execution Parameters)**

---

## Purpose

This document freezes **execution parameters** for the 5-year production ingestion.
It intentionally avoids redesign. The goal is to eliminate mid-run decisions,
reduce anxiety, and make the long ingestion predictable and repeatable.

Once this document is finalized, **parameters are frozen** until the run completes.

---

## Scope Definition

### Universe (Final, Locked)

**INCLUDE**
- ✔ **Common stock**
- ✔ **ADRs (American Depositary Receipts)**
- ✔ **REITs**

**EXCLUDE**
- ❌ Preferred stock (all classes, cumulative/convertible/etc.)
- ❌ Warrants
- ❌ Rights
- ❌ Units
- ❌ ETNs
- ❌ Closed-end funds
- ❌ Tracking / stub securities
- ❌ Business Development Companies (BDCs)

> The economic intent of the universe is:  
> **operating equity exposure**, excluding leveraged, derivative, income-structured,
> or bundled instruments.

---

### Important Note on Provider Limitations (Massive / Polygon)

Massive does **not** reliably provide explicit exclusion filters for all non-common
equity types (e.g., preferreds, warrants, units).

Therefore:

- The **initial universe pull may include** some non-common instruments
- This is expected and acceptable for the **first 5-year run**
- **No manual deletions** will be performed

**Required action during first 5-year run:**
1. Audit returned securities for non-common instruments
2. Identify which metadata fields are reliable for classification
3. Finalize deterministic exclusion logic
4. Encode exclusions explicitly for subsequent runs

This audit is a **mandatory execution step**, not an optional cleanup.

---

*Universe source:* The initial universe is obtained from Massive / Polygon’s full U.S. ticker universe 
(e.g., the “all tickers” endpoint); exact endpoint parameters and deterministic exclusion logic are finalized 
during Phase 6 execution after auditing returned securities.

## Identifiers

- Canonical identity based on existing **securities master**
- Ticker history resolved via `ticker_history`
- No ad-hoc symbol remapping during ingestion

---

## Date Range

- **Start date:** 5 years prior to run date (rolling)
- **End date:** Run date (inclusive, market-close aware)
- **Corporate actions:** Full available history (not truncated)

All jobs must accept explicit `start_date` / `end_date`.

---

## Job Order (Frozen)

1. Securities master
2. Ticker history
3. Prices (daily OHLCV)
4. Corporate actions (splits/dividends)
5. Adjustment factors
6. Fundamentals (raw quarterly)
7. Fundamentals (derived / YoY)
8. Derived views refresh

No reordering mid-run.

---

## Execution Rules

- **No manual DB edits**
- **No schema changes**
- **No skipping failed symbols silently**
- **No restarting mid-job without restoring from backup**

If a blocking error occurs:
1. Stop the run
2. Restore last full backup
3. Resume from last completed phase

---

## Rate Limiting & Throughput

- Respect provider rate limits strictly
- Prefer **steady throughput** over speed
- Throttling > retries > backoff (in that order)

Parallelism:
- Allowed only if already implemented
- Otherwise, single-threaded execution

---

## Failure Handling (High Level)

- **Transient API error:** Retry with backoff
- **Permanent symbol error:** Log and continue
- **Schema / integrity error:** Stop immediately
- **Unexpected exception:** Stop immediately

Detailed reactions are documented separately in
`KNOWN_FAILURE_MODES.md`.

---

## Logging & Observability

Each job must emit:
- Job name
- Run ID
- Start/end timestamps
- Rows processed
- Errors (symbol-scoped where possible)

Progress visibility is mandatory.

---

## Validation Gates

Validation must pass at:
- End of each major phase
- End of full ingestion

If validation fails:
- Do not “patch”
- Restore from backup
- Fix root cause
- Re-run phase

---

## Pre-Run Checklist

Before starting Phase 6 execution:

- [ ] Latest code pushed
- [ ] Backup & restore validated
- [ ] Bootstrap checklist committed
- [ ] This document committed
- [ ] Universe audit step acknowledged
- [ ] External distractions minimized

---

## Post-Run Commitments

After successful ingestion:

- Run full validation
- Create **final full backup**
- Copy backup to Dropbox
- Record backup filename
- Tag repo

Only then does the system move forward.

---

### End of document
