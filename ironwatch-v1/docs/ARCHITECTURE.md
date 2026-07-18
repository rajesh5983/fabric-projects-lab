# IronWatch v1 — Solution Architecture

## 1. Medallion Architecture Overview

```
   ┌─────────────────────────────────────────────────────────────────────────────────────┐
   │                     Microsoft Purview (v2) — Governance & Lineage                    │
   └────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────┘
        │              │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼              ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │   Python    │ │   Bronze    │ │   Silver    │ │    Gold     │ │  Semantic   │ │  Power BI   │
 │ Generators  ├▶│  Lakehouse  ├▶│  Warehouse  ├▶│  Warehouse  ├▶│   Model     ├▶│   Report    │
 │             │ │ironwatch_   │ │ironwatch_   │ │ironwatch_   │ │ DirectLake  │ │ Operations  │
 │             │ │bronze       │ │silver       │ │gold         │ │ + DAX       │ │ Dashboard   │
 └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

The governance bar spans every layer to signal that v1 is built so Purview
(planned for v2) can attach lineage, classification, and sensitivity labels
end-to-end without re-architecture.

## 2. Layer-by-Layer Description

| Layer | Fabric Item | Purpose |
|---|---|---|
| Ingestion | Python Generators (`synthetic_data/generators/`) | Produce synthetic OREXA Heavy Industries telemetry, oil sample, fault code, asset master, and service history files (PulseNet/FluidLab/FleetCare, per `docs/OREXA_SPEC.md`) that stand in for real machine data feeds |
| Bronze | `ironwatch_bronze` (**Lakehouse**) | Raw, schema-validated landing zone; append-only Delta tables mirroring the source file structure (ADR-002) |
| Silver | `ironwatch_silver` (**Warehouse**, per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)) | Cleansed, deduplicated, type-aligned tables exposed via SQL endpoint; built by `dbt-fabric` models, ready for Gold |
| Gold | `ironwatch_gold` (**Warehouse**) | Aggregated facts & dimensions, health-score and SLA computations exposed via SQL endpoint (ADR-001); every table carries a `_loaded_utc` watermark |
| Semantic | Power BI Semantic Model (`semantic_model/`) | DAX measures (e.g. HealthScore, MTBF, SLA Compliance) defined over the Gold Warehouse via DirectLake — no calculated columns |
| Presentation | Power BI Report | Operational equipment-health dashboard consumed by analytics and operations stakeholders |

## 3. Data Flow Narrative — A Sensor Reading's Journey

1. **Generation** — A Python generator simulates a sensor reading (e.g.
   `coolant_temp_c = 94.55` for Titan haul truck `T220-001` at
   `2026-03-09T00:00:00Z`) and writes it into `synthetic_data/output/` as a
   Parquet/CSV/JSON record, standing in for an ADLS Gen2 flat-file drop
   (ADR-002).
2. **Bronze ingestion** — `nb_bronze_telemetry_v1` reads the dropped file,
   validates it against the telemetry JSON Schema, and appends it as a raw,
   immutable row in `ironwatch_bronze` (Lakehouse), partitioned by event date.
3. **Silver refinement** — A `dbt-fabric` model (per
   [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)) reads the new
   Bronze row via a `source()` reference, deduplicates, aligns types (e.g.
   casts `engine_temp` to `decimal`), handles nulls, and writes a conformed
   record into `ironwatch_silver` (**Warehouse**).
4. **Gold aggregation** — `nb_gold_fact_telemetry_v1` and
   `nb_gold_health_score_v1` aggregate the Silver record into hourly facts
   and roll it into the equipment HealthScore for `T220-001`, landing in
   `fact_telemetry` / `fact_health_score` tables in `ironwatch_gold`
   (Warehouse), each stamped with `_loaded_utc`.
5. **Semantic modeling** — The Power BI semantic model connects to
   `ironwatch_gold` via DirectLake and evaluates DAX measures (e.g.
   `HealthScore`, `MTBF`) directly over the Gold tables — no import refresh
   required.
6. **Visualization** — An operations analyst opens the Power BI report; the
   reading's contribution to `T220-001`'s HealthScore appears as a tile and a
   trend-line point on the equipment-health visual within minutes of
   generation.

## 4. V2 Extension Points

| Extension | How v1 leaves the door open |
|---|---|
| **Eventhouse / Real-Time Intelligence (RTI)** | The Bronze landing contract (schema-validated Delta tables fed by file drops) is decoupled from the generator, so a streaming Eventhouse/RTI source can feed the same Bronze layer without changing Silver or Gold. |
| **Fabric Data Agent (MCP)** | The Gold Warehouse's well-defined fact/dimension schema and DAX semantic layer give a Fabric Data Agent a stable, documented surface to expose as an MCP server for natural-language querying. |
| **Ontology MCP** | Asset master and fault-code dimensions are modeled with stable identifiers and explicit relationships, so a future Ontology MCP server can map them onto a formal equipment ontology without reshaping the Gold schema. |
| **Snowflake Iceberg** | Gold tables sit on open Delta/SQL foundations, leaving a clear path to publish them as Iceberg tables for cross-platform consumption (e.g. Snowflake) without redesigning the medallion pipeline. |
| **dbt Core** | ~~Silver and Gold transformations are organized as discrete, testable notebook steps per layer — a structure that maps cleanly onto dbt models and tests if the transformation layer is migrated to dbt Core.~~ **Realized in v1, not v2** ([ADR-009](ADR/ADR-009-dbt-gold-transformation-layer.md), [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)): Gold and Silver transformations are both already authored as `dbt-fabric` models with a `ref()`/`source()` dependency graph and built-in tests — this extension point is no longer speculative. |

## 5. Azure Infrastructure

```
┌───────────────────────────┐  ┌─────────────────────────────────┐  ┌───────────────────────────┐
│     rg-fabric-sandbox     │  │         rg-shared-infra         │  │      rg-ironwatch-dev     │
│  ───────────────────────  │  │  ───────────────────────────── │  │  ───────────────────────  │
│  Fabric Capacity (F2)     │  │  mal-kv-shared (Key Vault)      │  │  Provisioned but unused   │
│  fabricf2sandbox          │  │  Automation Account             │  │  for this project — see   │
│  Landing storage          │  │  Logic App                      │  │  ADR-003                 │
│  fabricf2landingsa        │  │  (shared secrets, scheduling,   │  │                           │
│  (sp-ironwatch-dev scope; │  │  alerting/automation across     │  │                           │
│  actual IronWatch home)   │  │  ModernAnalyticsLab projects)   │  │                           │
└─────────────┬─────────────┘  └────────────────┬────────────────┘  └─────────────┬─────────────┘
              │                                  │                                  │
              └──────────────────────────────────┴──────────────────────────────────┘
                                ModernAnalyticsLab Azure Subscription
```

`sp-fabric-mal` (platform) and `sp-ironwatch-dev` (pipeline) authenticate
against secrets stored in `mal-kv-shared` — never hardcoded, never committed.
IronWatch resources live in `rg-fabric-sandbox` (the F2 capacity and landing
storage account); `rg-ironwatch-dev` is provisioned but currently unused for
this project (see [ADR-003](ADR/ADR-003-resource-group-placement.md)).

---

## IronCore Candidates
Patterns built in v1 that are candidates for extraction into the 
IronCore framework in July 2026:
- scripts/infra/config.py → forge_core.config
- scripts/infra/audit.py → forge_core.audit
- [add entries here as v1 build progresses]

---

## Changelog
- **v1.1 (2026-07-18):** Silver (`ironwatch_silver`) updated from Lakehouse
  to **Warehouse** per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)
  — medallion diagram, layer table (§2), and the Silver-refinement step of
  the data-flow narrative (§3) updated to match; dbt Core v2 extension
  point (§4) marked realized in v1 for both Silver and Gold. Bronze is
  unaffected by this revision.
- **v1.0:** Initial architecture, approved for build.

---

Architecture version: v1.1 | Status: APPROVED FOR BUILD
