# Phase 4B — Fundamentals Ingestion (Quarterly, Raw)

**Status:** COMPLETE & LOCKED
**Repo:** `stocks-db-ingestion`
**Phase:** 4B
**Provider:** Massive
**Job:** `fundamentals_quarterly_raw`

---

## 1. Purpose of Phase 4B

Phase 4B introduces **authoritative, minimally-processed quarterly fundamentals** into the research database. The goal is to ingest *just enough* financial statement data to support growth calculations and validation workflows **without prematurely committing to a full financial-statement model**.

This phase is intentionally conservative:

* Preserve the original provider payload
* Extract only a small, well-defined metric set
* Establish a stable quarter spine
* Defer all metric explosion and normalization

Phase 4B exists to make later work **safer, auditable, and reversible**.

---

## 2. Authoritative Design Decisions (LOCKED)

The following design choices are final for Phase 4B and must not be altered retroactively.

### 2.1 Canonical Identity

* **Security identifier:** `securities.composite_figi`
* All fundamentals rows are keyed to `composite_figi`
* Ticker symbols are *not* used as identity

This guarantees stability across ticker changes and corporate actions.

---

### 2.2 Quarter Spine

* Quarter spine is derived from the **income statement**
* Fiscal period format: `YYYYQn` (e.g., `2023Q4`)
* Every metric stored in Phase 4B must map to a valid income-statement quarter

Balance sheet and cash flow statements are intentionally ignored at this stage.

---

## 3. Target Table

**Schema:** `stocks_research.fundamentals_quarterly_raw`

| Column         | Type    | Nullable | Description                   |
| -------------- | ------- | -------- | ----------------------------- |
| composite_figi | text    | NO       | Canonical security identifier |
| fiscal_period  | text    | NO       | Fiscal quarter (`YYYYQn`)     |
| report_date    | date    | YES      | Provider-reported filing date |
| metric_name    | text    | NO       | Metric identifier             |
| metric_value   | numeric | YES      | Parsed numeric value          |
| source         | text    | YES      | Data provider (`massive`)     |
| raw_payload    | jsonb   | YES      | Entire provider row           |

---

## 4. Metrics Stored (INTENTIONALLY MINIMAL)

Phase 4B extracts **exactly two metrics** per quarter:

* `revenue`
* `diluted_eps`

### Storage Rules

* One row per:

  ```
  (composite_figi, fiscal_period, metric_name)
  ```
* `metric_name` is stored as lowercase snake_case
* `metric_value` is numeric and nullable (provider truth preserved)

No other metrics are parsed or stored at this phase.

---

## 5. Raw Payload Preservation

Every quarterly row received from Massive is stored **verbatim** in `raw_payload`.

### Rationale

* Enables forensic debugging
* Allows future reprocessing without re-pulling data
* Preserves provider-specific nuances and metadata

No transformations, filtering, or pruning are applied to `raw_payload`.

---

## 6. Ingestion Job Contract

**Job:** `fundamentals_quarterly_raw`

**Runner signature:**

```python
run(conn, job_id) -> metrics
```

### Responsibilities

* Resolve `composite_figi`
* Pull quarterly fundamentals from Massive
* Insert raw payload
* Extract and insert `revenue` and `diluted_eps`
* Enforce idempotency at the row level

### Non-Responsibilities

* Pagination handling
* Metric normalization
* Cross-statement reconciliation
* YoY / QoQ calculations

---

## 7. What Phase 4B Explicitly Does NOT Do

Phase 4B intentionally avoids the following:

* ❌ Full financial statement modeling
* ❌ Metric explosion from raw payload
* ❌ Balance sheet or cash flow ingestion
* ❌ Statement-type normalization
* ❌ Provider pagination (`next_url`)
* ❌ Parallelization or performance tuning
* ❌ Derived metrics (YoY, TTM, margins)

These omissions are **by design**, not gaps.

---

## 8. Deferred Work (Future Phases)

The following items are explicitly deferred and must not be backfilled into Phase 4B.

### Phase 4C (Planned)

* Full metric explosion from `raw_payload`
* Statement-type normalization (IS / BS / CF)
* Metric taxonomy and naming standards
* Derived metrics (YoY, Q4 synthesis, etc.)

### Later Phases

* Massive pagination via `next_url`
* Parallelized ingestion
* Provider abstraction
* Incremental backfill strategies

---

## 9. Guarantees Established by Phase 4B

After successful Phase 4B ingestion, the system guarantees:

* Stable quarterly spine per security
* Exactly one revenue and one diluted EPS per quarter (post-validation)
* Immutable raw provider data
* Clean separation between raw ingestion and derived analytics

These guarantees are foundational for all downstream research.

---

## 10. Phase Status

**Phase 4B is COMPLETE and LOCKED.**

No new ingestion logic, metrics, or schema changes should be introduced under the Phase 4B umbrella.

All future enhancements must proceed via documented subsequent phases.

---

*End of Phase 4B documentation.*
