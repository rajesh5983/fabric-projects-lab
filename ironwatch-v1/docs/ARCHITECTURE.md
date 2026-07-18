# IronWatch v1 — Solution Architecture

## 1. Medallion Architecture Overview

```text
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

*`ironwatch_silver` was re-provisioned as a Warehouse on 2026-07-18 per
[ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md) — this diagram
reflects the current, actually-provisioned architecture. Silver's dbt
models themselves are not yet written; see §2 below.*

The governance bar spans every layer to signal that v1 is built so Purview
(planned for v2) can attach lineage, classification, and sensitivity labels
end-to-end without re-architecture.

## 2. Layer-by-Layer Description

| Layer | Fabric Item | Purpose |
|---|---|---|
| Ingestion | Python Generators (`synthetic_data/generators/`) | Produce synthetic OREXA Heavy Industries telemetry, oil sample, fault code, asset master, and service history files (PulseNet/FluidLab/FleetCare, per `docs/OREXA_SPEC.md`) that stand in for real machine data feeds |
| Bronze | `ironwatch_bronze` (**Lakehouse**) | Raw, schema-validated landing zone; append-only Delta tables mirroring the source file structure (ADR-002) |
| Silver | `ironwatch_silver` (**Warehouse**, re-provisioned 2026-07-18 per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)) | Cleansed, deduplicated, type-aligned tables exposed via SQL endpoint; built by `dbt-fabric` models — `sources.yml` migrated to read Bronze directly, `dbt debug --target silver` passes, but the Silver model files themselves (`stg_telemetry` etc.) are not yet written |
| Gold | `ironwatch_gold` (**Warehouse**) | Aggregated facts & dimensions, health-score and SLA computations exposed via SQL endpoint (ADR-001); every table carries a `_loaded_utc` watermark |
| Semantic | Power BI Semantic Model (`semantic_model/`) | DAX measures (e.g. HealthScore, MTBF, SLA Compliance) defined over the Gold Warehouse via DirectLake — no calculated columns |
| Presentation | Power BI Report | Operational equipment-health dashboard consumed by analytics and operations stakeholders |

## 3. Data Flow Narrative — A Sensor Reading's Journey

1. **Generation** — A Python generator simulates a sensor reading (e.g.
   `coolant_temp_c = 94.55` for Titan haul truck `T220-001` at
   `2026-03-09T00:00:00Z`) and writes it into `synthetic_data/output/` as a
   Parquet/CSV/JSON record, standing in for an ADLS Gen2 flat-file drop
   (ADR-002).
2. **Bronze ingestion** — `pl_bronze_telemetry_load`, a Data Pipeline Copy
   Activity (`scripts/infra/build_bronze_pipelines.py`, ADR-007 — no
   notebooks), reads the dropped file and writes it into `ironwatch_bronze`
   (Lakehouse) via a `LakehouseTableSink` with `tableActionOption: Overwrite`
   — each run replaces the table's full contents; it does not append or
   partition by date, despite ADR-002's original "append-only" framing.
3. **Silver refinement (infrastructure ready, model not yet written)** —
   Per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md), a `dbt-fabric`
   model will read the new Bronze row via a `source()` reference,
   deduplicate, align types (e.g. cast `engine_temp` to `decimal`), handle
   nulls, and write a conformed record into `ironwatch_silver`
   (**Warehouse**). `ironwatch_silver` was re-provisioned as a Warehouse
   and `sources.yml` migrated to read Bronze directly on 2026-07-18 — dbt
   can already reach both ends (`dbt debug --target silver` passes) — but
   this specific Silver model file doesn't exist yet, so this step doesn't
   run for real data until it's written.
4. **Gold aggregation** — `dbt-fabric` mart models (`fact_telemetry`,
   `fact_health_score` under `transform/ironwatch_gold/models/marts/`,
   ADR-009 — no notebooks) aggregate the Silver record into hourly facts
   and roll it into the equipment HealthScore for `T220-001`, landing in
   `ironwatch_gold` (Warehouse), each stamped with `_loaded_utc`. (Marts
   are currently placeholder stubs, not real transformation logic — see §4.)
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
| **dbt Core** | ~~Silver and Gold transformations are organized as discrete, testable notebook steps per layer — a structure that maps cleanly onto dbt models and tests if the transformation layer is migrated to dbt Core.~~ **Decided for v1, infrastructure ready, model logic still pending** ([ADR-009](ADR/ADR-009-dbt-gold-transformation-layer.md), [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)): Gold's `dbt-fabric` project is scaffolded (`transform/ironwatch_gold/`) but its marts are still placeholder stubs, not real transformation logic. Silver was re-provisioned as a Warehouse and `sources.yml` migrated to a Bronze source 2026-07-18 — `dbt debug --target silver` passes — but no Silver dbt models are written yet either. This extension point is no longer speculative and the plumbing works end-to-end, but neither layer has real transformation logic in place yet. |

## 5. Azure Infrastructure

```text
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

## 6. Audit & Execution Logging

```text
Bronze (Lakehouse)                    Silver (Warehouse)      Gold (Warehouse)
┌───────────────────────────┐         ┌──────────────┐        ┌──────────────┐
│ _ironwatch_meta/          │◀────────┤ run_dbt.py   │        │ run_dbt.py   │
│ execution_log             │◀────────────────────────────────┤              │
│ (single shared Delta      │         └──────────────┘        └──────────────┘
│  table, Bronze-hosted)    │
└───────────────────────────┘
```

Every pipeline run logs one row to `_ironwatch_meta/execution_log` — a
single Delta table hosted in `ironwatch_bronze` regardless of which layer
ran, because Warehouses (Silver, Gold) can't be a target for `audit.py`'s
direct Delta-file write mechanism (see
[ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)'s "Audit table
contract").

| Column | Type | Notes |
|---|---|---|
| `run_id` | STRING | UUID, new on every call — `log_execution()` is append-only, no update/correlation mechanism |
| `pipeline_name` | STRING | e.g. `pl_bronze_telemetry_load`, `dbt_run_silver` |
| `layer` | STRING | `bronze` / `silver` / `gold` |
| `status` | STRING | `success` / `failed` |
| `rows_processed` | LONG | `0` for CTAS-materialized dbt models — the ODBC driver reports `rows_affected=-1` for `CREATE TABLE AS SELECT`, treated as "not reported" rather than a negative count |
| `error_message` | STRING, nullable | |
| `engine` | STRING | `copy_activity` (Bronze) / `dbt-fabric` (Silver, Gold) |
| `recorded_at` | TIMESTAMP | UTC |

- **Silver/Gold:** `scripts/infra/run_dbt.py` wraps `dbt run` as a
  subprocess, parses `run_results.json`, and calls `log_execution()`
  **exactly once, after** completion — a before/after pair would produce
  two disconnected rows with no way to tie them together.
- **Bronze:** real audit rows exist in the table for all 5 Copy Activity
  pipelines (`engine='copy_activity'`), but
  `scripts/infra/build_bronze_pipelines.py` as currently committed does
  **not** call `log_execution()` anywhere — the actual write path for
  those existing rows isn't present in this repo. Open question, not
  resolved here.

## 7. CI/CD & Review Workflow

```text
feature/* ──▶ develop ──▶ PR to main ──▶ CodeRabbit review
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
              Approved, no excluded paths                Changes requested, OR
                        │                                 touches an excluded path
                        ▼                                 (Key Vault/secrets,
              auto-merge (squash)                         .coderabbit.yaml,
                                                            docs/ADR/**,
                                                            .github/workflows/**)
                                                                      │
                                                                      ▼
                                                              manual merge required
```

| Command | Purpose |
|---|---|
| `/ship` (`.claude/commands/ship.md`) | Commit → push → open PR → poll CodeRabbit → queue `gh pr merge --auto --squash` unless the diff touches an excluded path |
| `/ship-status` (`.claude/commands/ship-status.md`) | Check PRs with queued auto-merge; reconcile `develop`↔`main` divergence |

`.coderabbit.yaml`: `profile: chill`, `request_changes_workflow: true`,
scoped to `ironwatch-v1/**` (this is a monorepo shared with two unrelated
projects, deliberately excluded). `develop`/`main` reconciliation after a
squash-merge uses `git reset --hard origin/main`, not `rebase` — rebasing
a squash-merged branch's original incremental commits reliably produces
false conflicts even when the underlying content is identical. CodeRabbit
findings aren't accepted uncritically — false positives get pushed back on
via inline reply with technical reasoning, and CodeRabbit will withdraw a
finding when shown to be wrong.

---

## IronCore Candidates
Patterns built in v1 that are candidates for extraction into the 
IronCore framework in July 2026:
- scripts/infra/config.py → forge_core.config
- scripts/infra/audit.py → forge_core.audit
- scripts/infra/run_dbt.py → forge_core.run_dbt (dbt-run + audit-log wrapper pattern, layer-agnostic)
- [add entries here as v1 build progresses]

---

## Changelog
- **v1.3 (2026-07-18):** Documentation audit pass — fixed the last two
  stale notebook references in §3 (Bronze ingestion, Gold aggregation;
  both predate this session, ADR-007/ADR-009 already superseded them).
  Added §6 (Audit & Execution Logging) and §7 (CI/CD & Review Workflow) as
  real diagram/table sections rather than leaving that entirely
  undocumented. Added `run_dbt.py` to IronCore Candidates.
- **v1.2 (2026-07-18):** `ironwatch_silver` was actually re-provisioned
  from Lakehouse to **Warehouse** per
  [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md), and
  `sources.yml`/`profiles.yml` migrated to match (`scripts/infra/config.py`
  and `dbt debug --target silver` both confirm this). Flips v1.1's
  "target, not yet executed" hedging back to present tense across the
  medallion diagram, layer table (§2), data-flow narrative (§3), and dbt
  Core extension point (§4) — while keeping accurate that no Silver dbt
  model files exist yet (that part is still pending, next session's task).
- **v1.1 (2026-07-18):** Documented Silver's (`ironwatch_silver`) *target*
  item type change from Lakehouse to Warehouse per ADR-010, marked
  explicitly as not yet executed. Superseded by v1.2 above the same day,
  once the infrastructure work actually happened.
- **v1.0:** Initial architecture, approved for build.

---

Architecture version: v1.3 | Status: APPROVED FOR BUILD
