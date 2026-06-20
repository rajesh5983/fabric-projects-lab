# ADR-007: Spark-Free Compute Architecture

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
IronWatch v1 runs on `fabricf2sandbox`, an **F2** capacity — the smallest
Fabric SKU. Spark notebooks are capacity-unit intensive and risk throttling
on F2 for no real benefit here: the largest Bronze source file
(`telemetry.parquet`) is only ~375KB at the current synthetic-data scale.
ADR-001 already committed Gold to a Warehouse/T-SQL engine specifically to
avoid "the Spark tax" for consumption — but left Bronze and Silver on
PySpark notebooks by default, which would mix a Spark engine into the
pipeline anyway for no volume-justified reason.

## Decision
Bronze, Silver, and Gold all avoid Spark compute end-to-end:
- **Bronze:** ingestion via Data Pipeline **Copy Activity** (or OneLake
  shortcuts where applicable) into the Lakehouse — no Spark notebooks.
- **Silver:** transforms via **Dataflow Gen2** (Power Query engine, not
  Spark).
- **Gold:** Warehouse populated via T-SQL stored procedures/views, per
  ADR-001 (unchanged).

This explicitly **supersedes** the compute-engine claim in ADR-001
("Bronze and Silver remain Lakehouses written by PySpark notebooks") — see
the amendment in ADR-001 itself. Bronze and Silver remain **Lakehouses for
storage**; what changes is the compute engine that writes to them.

## Rationale
- Source volumes are small regardless of capacity tier — Spark's
  distributed-compute model has nothing to distribute here.
- F2 specifically makes Spark capacity-unit cost a real constraint, not a
  theoretical one; Copy Activity and Dataflow Gen2 are far lighter on
  capacity consumption for this workload size.
- Keeps the whole pipeline consistent with the Warehouse/T-SQL approach
  ADR-001 already chose for Gold, rather than mixing a Spark Bronze/Silver
  with a non-Spark Gold.

## Consequences
- No `nb_bronze_*_v1` / `nb_silver_*_v1` Spark notebooks will be built;
  Bronze ingestion is Data Pipeline Copy Activity, Silver transforms are
  Dataflow Gen2.
- `docs/WORKSPACE_DESIGN.md` §3 (notebook naming/inventory) and
  `docs/ARCHITECTURE.md`'s layer-by-layer narrative still describe a
  notebook-per-layer Bronze/Silver build — both predate this ADR and have
  **not** been rewritten to match; flagged for a follow-up pass, not fixed
  in this one.
- `README.md`'s Tech Stack table and architecture diagram are updated as
  part of this same change to stop claiming Spark 3.x compute.
- Gold is unaffected — ADR-001's Warehouse/T-SQL decision stands as-is.
