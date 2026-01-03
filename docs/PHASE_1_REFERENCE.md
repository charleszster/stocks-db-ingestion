# Stocks DB — Phase 1: Reference Data & Schema Design

Phase 1 represents the **foundational design phase** of the Stocks DB system.

This phase established the database schema, identifier strategy, universe
bootstrapping rules, and architectural constraints that all later phases rely on.

Phase 1 did not ingest live market data.

---

## Scope

Phase 1 defined:

- Core PostgreSQL schema (`stocks_research`)
- Entity relationships and constraints
- Identifier and symbol handling decisions
- Development universe bootstrapping
- Ingestion invariants and design rules

---

## Artifacts

Phase 1 artifacts include:

- Database schema:
  - `sql/stock_research_schema.sql`
- Entity-relationship design:
  - `docs/erd/stocks_research_schema.pgerd`
- Development universe definitions:
  - `config/universe_dev.csv`
  - `config/universe_dev.json`

These artifacts define the **contract** that later ingestion and processing
phases must obey.

---

## Non-Goals

Phase 1 did NOT:

- Ingest raw market data
- Adjust prices or apply corporate actions
- Generate indicators or signals
- Define trading universes beyond development bootstrapping
- Implement ingestion runners or orchestration

Those concerns begin in Phase 2.

---

## Boundary to Phase 2

Phase 1 is considered complete as of Git tag:

```
v0.1.0
```

Phase 2 begins with the introduction of executable ingestion logic and
run/job lifecycle tracking.

---

## Philosophy

Phase 1 prioritizes:

- Explicit schema design
- Stable identifiers
- Time-aware modeling
- Reproducibility

All subsequent phases depend on the correctness of these foundations.
