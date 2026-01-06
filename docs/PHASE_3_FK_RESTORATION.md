# Phase 3 — FK Restoration Sequence (Safe and Boring)

This document defines the exact sequence to restore the foreign key
from `stocks_research.prices_daily.security_id` to
`stocks_research.securities.security_id` without breaking Phase 2 ingestion
or risking data loss.

No schema refactors. No ingestion changes. No downtime.

---

## Preconditions (Must Be True Before Starting)

- Phase 2 ingestion is complete and locked
- `stocks_research.securities.security_id` contains all intended canonical identities
- Phase 3 constraints document is committed and pushed
- No active writes are modifying historical prices during validation windows

---

## Goal

Enforce:
prices_daily.security_id
→ securities.security_id


while:
- preserving all historical data
- allowing gradual cleanup if needed
- avoiding table-wide blocking scans

---

## Step 1 — Orphan Detection (Read-Only)

Purpose:
Identify whether any `prices_daily.security_id` values do not exist in `securities`.

Conceptual query (do not commit results yet):

- LEFT JOIN prices_daily → securities
- WHERE securities.security_id IS NULL
- GROUP BY orphan security_id
- COUNT rows

Expected outcomes:
- **Best case**: zero rows (ideal)
- **Acceptable case**: small, explainable set
- **Bad case**: many orphans (pause and investigate before continuing)

No schema changes yet.

---

## Step 2 — Classify Any Orphans (If Present)

Each orphan must fall into exactly one category:

1) **Legitimate historical instrument**
   - Missing from `securities`
   - Requires inserting a new canonical security row

2) **Legacy / placeholder identity**
   - Exists due to early Phase 2 assumptions
   - Must be mapped or merged intentionally

3) **Data error**
   - Bad ingest
   - Candidate for deletion or correction

Resolution rules:
- Never delete price data blindly
- Prefer adding missing securities over mutating prices
- Document every non-trivial fix

This step may take time. That’s normal.

---

## Step 3 — Remediate Orphans (If Any)

Actions (as needed):
- Insert missing rows into `securities`
- Ensure `security_id` values match those used in `prices_daily`
- Confirm lifecycle fields (`start_date`, `end_date`, `is_active`) are sane

Verification:
- Re-run orphan detection
- Confirm zero orphan rows remain

Do not proceed until this is true.

---

## Step 4 — Add the FK (NOT VALID)

Add the foreign key constraint in **NOT VALID** mode.

Important properties:
- Prevents *new* invalid rows
- Does NOT scan existing data
- Does NOT block writes for extended periods

At this point:
- New price ingests must reference a valid `security_id`
- Historical data is unchanged

This step is safe even on large tables.

---

## Step 5 — Observation Period (Optional but Recommended)

Duration:
- One or more trading days

What you’re checking:
- Phase 2 ingestion continues normally
- No FK violations occur
- No unexpected constraint failures

If something breaks:
- Drop the NOT VALID FK
- Fix the root cause
- Retry

No data corruption is possible at this stage.

---

## Step 6 — Validate the FK

When confident:

- Run FK validation
- Database scans existing rows and confirms compliance

Expected behavior:
- Validation may take time depending on table size
- Normal reads continue
- Writes may queue briefly (engine-dependent)

If validation fails:
- The DB reports offending rows
- Fix only those rows
- Re-run validation

---

## Step 7 — Lock It In

Once validated:
- The FK is fully enforced
- `prices_daily.security_id` is now guaranteed canonical

From this point forward:
- All price data is provably linked to a known security
- Identity joins are safe
- Ticker resolution via `ticker_history` is trustworthy

---

## Invariants After Completion

Guaranteed by the database:
- Every price row references a valid security
- No duplicate daily bars per security
- Price sanity constraints are enforced

Guaranteed by process:
- Security identity is stable
- Ticker changes do not affect prices
- Vendor churn does not alter canonical IDs

---

## Explicitly Not Done Here

- No backfilling of company relationships
- No provider adapter enforcement
- No ingestion changes
- No analytics assumptions

Those belong to later deliverables.

---

## Rollback Strategy (If Ever Needed)

- FK can be dropped without data loss
- Canonical semantics remain intact
- Historical price data is untouched

Rollback is reversible and safe.

---

## Phase 3 Status After This Step

- Identity semantics locked
- FK integrity enforced
- Database ready for:
  - Daily discretionary scans
  - Charting across ticker changes
  - Future analytics layers

This completes Phase 3 FK restoration.
