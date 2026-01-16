# Phase 4B — Fundamentals Alignment & Growth Metrics

## Purpose

Phase 4B produces **temporally safe, tradable fundamentals** that can be joined to
**adjusted daily prices** with **zero lookahead bias with respect to filed financial statements**.

This phase exists to ensure:
- Backtests are reproducible
- ML features are leakage-free
- Fundamentals behave as step functions over time

If Phase 4B is wrong, everything downstream is invalid.

---

## Preconditions

Phase 4B assumes the following are already complete and trusted:

- Phase 4A complete and tagged
- `prices_daily_adjusted` exists and is canonical
- Trading calendar is authoritative
- Canonical quarterly fundamentals exist conceptually:
  - Q1–Q3 from 10-Q
  - FY from 10-K
  - Q4 derived (designed separately)
- Restatement policy defined (latest wins)

If any of the above are not true, Phase 4B must abort.

---

## Inputs (Logical Contract)

### fundamentals_quarterly_canonical

One row per:
(security_id, fiscal_year, fiscal_quarter)


Required columns:
- security_id
- fiscal_year
- fiscal_quarter (1–4)
- period_end_date
- report_date
- revenue
- eps_diluted
- is_derived (TRUE for Q4)
- provider
- ingestion_run_id

Input invariants:
- report_date >= period_end_date
- Q1–Q4 exist for completed fiscal years
- Q4 values derived from FY − Q1 − Q2 − Q3
- Q4 report_date equals 10-K filing date
- Restatements resolved upstream

Violations cause a hard failure.

---

## Outputs

### fundamentals_quarterly_aligned

A derived, consumption-facing table suitable for joining to prices.

Required columns:
- security_id
- fiscal_year
- fiscal_quarter
- period_end_date
- report_date
- effective_start_date
- effective_end_date
- revenue
- eps_diluted
- revenue_yoy
- eps_yoy
- source_run_id

This table is not a long-term storage layer.

---

## Execution Order (Mandatory)

1. Validate canonical quarterly fundamentals
2. Compute YoY growth (quarter domain only)
3. Align quarters to trading calendar
4. Validate effective windows
5. Materialize aligned output

Reordering these steps is prohibited.

---

## YoY Growth Rules

- Growth is computed only in the fiscal-quarter domain
- (Y, Q) compares only to (Y−1, Q)
- No forward filling
- NULL if undefined (missing prior quarter, zero denominator)
- Alignment happens after growth computation

---

## Alignment Rules

For each quarterly row:
- effective_start_date = first trading date on or after report_date
- effective_end_date = day before next quarter’s effective_start_date

Trading dates come exclusively from `prices_daily_adjusted`.

---

## Invariants (Hard Failures)

- No overlapping effective windows per security
- No trading date maps to more than one quarter
- effective_start_date >= report_date
- No forward-looking fundamentals

---

## Explicit Non-Goals

Phase 4B does NOT:
- Compute TTM metrics
- Store full financial statements
- Align intraday data
- Adjust prices by volume
- Optimize performance
- Backfill missing fundamentals

---

## Logging & Observability

Phase 4B must record:
- Rows processed
- Securities skipped (with reason)
- Quarters with missing YoY
- Validation failures

Logging is operational, not analytical.

---

## Definition of Done

Phase 4B is complete when:
- All invariants can be asserted via SQL
- Aligned fundamentals form a step function
- Historical backtests replay identically
- Phase is tagged and immutable
