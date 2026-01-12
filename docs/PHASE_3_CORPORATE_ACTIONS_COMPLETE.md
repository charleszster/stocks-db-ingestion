## Phase 3 — Corporate Actions (Complete)

Phase 3 establishes a canonical, replay-safe corporate actions event stream in `stocks_research.corporate_actions`
supporting splits and dividends from Massive.

### What’s enforced

- **Canonical identity:** `(provider, provider_action_id)` is the primary key (provider-native event identity).
- **Replay safety:** idempotent upserts on `(provider, provider_action_id)`; repeated runs are data-stable.
- **Validation gates:**
  - **Pre-run DB invariants:** `validate_corporate_actions()` verifies no orphans, no missing provider IDs, and no duplicate provider IDs.
  - **Event-level payload validation:** `validate_split()` / `validate_dividend()` reject malformed provider events before insert.
- **Universe selection:** ingestion uses the selected universe file via `ingest.universe.load_tickers()`.

### How to run (dev)

```bash
python -m src.ingest.jobs.corporate_actions

Recommended: use a small universe_selected.json during hardening. Scale-up comes in Phase 4.