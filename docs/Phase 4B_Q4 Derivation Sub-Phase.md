# Phase 4B-0 — Q4 Derivation Sub-Phase
(Q4 from FY − Q1 − Q2 − Q3)

## Purpose

This sub-phase derives **Q4 quarterly fundamentals** for companies that do not
explicitly report Q4 results, using annual filings (10-K) and the first three quarters (10-Q).

Q4 derivation is mandatory for:
- Correct YoY growth
- Complete fiscal-quarter coverage
- Temporal alignment in Phase 4B

This phase exists so Phase 4B does not have to care where Q4 came from.

---

## Position in the Pipeline
Raw filings ingestion
↓
Quarterly canonical (Q1–Q3, FY)
↓
PHASE 4B-0: Q4 DERIVATION ← YOU ARE HERE
↓
fundamentals_quarterly_canonical (Q1–Q4)
↓
Phase 4B alignment + growth


This sub-phase is upstream of alignment and downstream of raw ingestion.

---

## Inputs (Logical Contract)

### Required Inputs

For each `(security_id, fiscal_year)`:

- Q1, Q2, Q3 quarterly data (from 10-Q)
- FY annual data (from 10-K)

Each input row must include:
- security_id
- fiscal_year
- fiscal_quarter (1–3 for Qs, NULL or FY marker for annual)
- period_end_date
- report_date
- revenue
- eps_diluted
- provider
- ingestion_run_id

---

## Output

### fundamentals_quarterly_canonical (augmented)

Adds one derived row per:
(security_id, fiscal_year, fiscal_quarter = 4)


Required output fields for Q4:
- security_id
- fiscal_year
- fiscal_quarter = 4
- period_end_date (fiscal year end)
- report_date (10-K filing date)
- revenue
- eps_diluted
- is_derived = TRUE
- derivation_method = 'FY_MINUS_Q1_Q2_Q3'
- source_filing = '10-K'

---

## Q4 Derivation Rules

### Revenue (Straightforward, No Drama)
Q4_revenue = FY_revenue − (Q1_revenue + Q2_revenue + Q3_revenue)


Rules:
- All components must exist
- Result may be negative (rare, but real)
- No smoothing, no adjustments

---

### EPS (More Annoying, Still Deterministic)
Q4_eps = FY_eps − (Q1_eps + Q2_eps + Q3_eps)


Caveats (documented, not “fixed”):
- Share count changes are ignored
- EPS may look odd in edge cases
- This mirrors how Compustat-style datasets behave

Correctness here means **consistency**, not perfection.

---

## Report Date Semantics (Critical)

- Q4 `report_date` = **10-K filing date**
- NOT fiscal year end
- NOT earnings call date
- NOT press release date

This ensures:
- No temporal leakage
- Clean integration with Phase 4B alignment

---

## Invariants (Hard Failures)

Q4 derivation must abort if:

- Any of Q1–Q3 missing
- FY data missing
- FY < sum(Q1–Q3) for revenue (beyond rounding tolerance)
- report_date missing for FY
- Duplicate Q4 already exists

If inputs are bad, we stop.  
We do not “best effort” financial statements.

---

## Soft Failures (Logged, Allowed)

- Negative Q4 revenue
- Extreme EPS values
- EPS sign flips
- Minor rounding discrepancies

These are data realities, not pipeline bugs.

---

## Idempotency & Restatements

- Q4 rows are fully re-derived on rerun
- If upstream FY or Q1–Q3 change, Q4 changes
- Latest ingestion_run wins
- No attempt to preserve historical incorrect Q4s

Correctness > nostalgia.

---

## Explicit Non-Goals

This phase does NOT:
- Adjust for share count changes
- Handle partial fiscal years
- Backfill missing quarters
- Perform alignment to prices
- Compute growth metrics

It does math. Then it gets out of the way.

---

## Definition of Done

Phase 4B-0 is complete when:
- Every completed fiscal year has Q1–Q4
- Q4 rows are clearly marked as derived
- Report dates are correct
- Phase 4B can assume Q4 exists without asking questions

---

## Reviewer’s Closing Remark

Q4 derivation is boring.
Boring is good.
Boring means nobody argues with your backtests later.


