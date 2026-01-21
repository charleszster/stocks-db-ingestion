# 3️⃣ Explicit Phase 5 backlog (WITHOUT designing it)

This is critical.  
We document **what is deferred** without accidentally committing to design.

---

## `docs/PHASE_5_BACKLOG.md`

```markdown
# Phase 5 — Explicit Backlog (Non-Commitment)

This document lists **intentionally deferred work**.
Nothing here is designed, approved, or implied.

---

## Candidate Phase 5 themes

### 1) Full financial statements (tall schema)
- Income statement line items
- Balance sheet
- Cash flow
- Raw vs derived separation preserved
- Requires reprocessing of stored raw payloads

Status: Deferred by design

---

### 2) Intraday prices
- New ingestion jobs
- New schema
- New adjustment logic
- No dependency on daily prices assumed

Status: Explicitly out of scope for Phases 1–4B

---

### 3) Advanced corporate actions
- Mergers
- Spinoffs
- Symbol reuse edge cases
- Requires identity expansion

Status: Deferred pending clear research need

---

### 4) Derived analytics layer
- TTM metrics
- Margins
- ROIC
- Factor libraries

Status: Analytical concern, not ingestion safety

---

## Important rule

> No Phase 5 work should modify Phases 1–4B behavior.
> Phase 4B is locked.

Any Phase 5 work must be additive.

---
