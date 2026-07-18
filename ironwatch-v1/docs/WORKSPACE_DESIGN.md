# IronWatch v1 — Workspace Design

Phase 2 decisions for the Fabric workspace layout, item inventory, naming,
access control, branching, and OneLake structure. These decisions are final
for the v1 build.

> **Amendment (2026-07-18):** §2 (Fabric Item Inventory), §3 (Notebook
> Naming Convention — Silver rows only), and §6 (OneLake Folder Structure)
> are amended per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md):
> `ironwatch_silver` was re-provisioned as a **Warehouse**, not a
> Lakehouse, and has no notebooks — transform logic is authored as
> `dbt-fabric` models instead (`sources.yml` migrated to read Bronze
> directly, `dbt debug --target silver` passes). No Silver dbt model files
> are written yet — that part is still pending, next session's task.
> Everything else in this document — Bronze as a Lakehouse, Gold as a
> Warehouse, RBAC, branch strategy — is unchanged and still in effect. This
> amendment updates the affected sections in place rather than reopening
> the whole document.

## 1. Fabric Workspace Naming

| Workspace | Purpose | Tier |
|---|---|---|
| `ModernAnalyticsLab-DEV` | Active build workspace — pipelines, dbt models, semantic model under development | Development |
| `ModernAnalyticsLab-Sandbox` | Exploratory / scratch workspace for testing Fabric features without affecting DEV | Sandbox |

Both workspaces run on the **F2** capacity (`fabricf2sandbox`) per
[ADR-001](ADR/ADR-001-gold-warehouse.md). There is no separate production
workspace for v1 — `ModernAnalyticsLab-DEV` is promoted to demo-ready state
via the `main` branch (see §5).

## 2. Fabric Item Inventory

| Item Name | Fabric Item Type | Layer | Purpose |
|---|---|---|---|
| `ironwatch_bronze` | **Lakehouse** | Bronze | Raw ingestion landing zone for synthetic telemetry, oil samples, fault codes, asset master, and service history (Delta tables, schema-validated on write) |
| `ironwatch_silver` | **Warehouse** (re-provisioned 2026-07-18 per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md)) | Silver | Cleansed, deduplicated, type-aligned tables exposed via SQL endpoint; built by `dbt-fabric` models — model files not yet written |
| `ironwatch_gold` | **Warehouse** | Gold | Aggregated facts/dimensions exposed via SQL endpoint for the Power BI semantic model (see [ADR-001](ADR/ADR-001-gold-warehouse.md) — Gold is a Warehouse, *not* a Lakehouse) |

> **Note:** Bronze is explicitly a **Lakehouse**; Silver and Gold are
> explicitly **Warehouses** — Silver was re-provisioned from Lakehouse to
> Warehouse on 2026-07-18 per
> [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md). Do not provision
> Bronze as a Warehouse or Silver/Gold as Lakehouses. Root `CLAUDE.md`'s
> `NEVER` list still only names Gold explicitly for this rule — it has not
> yet been updated to also name Silver; flagged as a follow-up, not fixed
> here.

## 3. Notebook Naming Convention & Planned Notebooks

**Convention:** `nb_[layer]_[purpose]_[version]`
(e.g. `nb_bronze_telemetry_v1`)

| Notebook | Layer | Purpose |
|---|---|---|
| ~~`nb_bronze_telemetry_v1`~~ | ~~Bronze~~ | **Superseded** — Bronze has no notebooks (Data Pipeline Copy Activity per [ADR-007](ADR/ADR-007-spark-free-architecture.md), `scripts/infra/build_bronze_pipelines.py`). This row and the 4 other planned Bronze notebooks (`nb_bronze_oil_samples_v1`, `nb_bronze_fault_codes_v1`, `nb_bronze_asset_master_v1`, `nb_bronze_service_history_v1`) never existed as real artifacts |
| ~~`nb_silver_telemetry_v1`~~ | ~~Silver~~ | **Superseded** — Silver has no notebooks (Dataflow Gen2 per ADR-007, then `dbt-fabric` models per [ADR-010](ADR/ADR-010-silver-warehouse-dbt-scope.md), infrastructure live as of 2026-07-18). No Silver dbt model files are written yet; exact model names/paths under `transform/ironwatch_gold/models/silver/` are a build-session detail, not fixed here |
| ~~`nb_gold_dim_asset_v1`~~ | ~~Gold~~ | **Superseded** — Gold has no notebooks (`dbt-fabric` models under `transform/ironwatch_gold/models/marts/` per [ADR-009](ADR/ADR-009-dbt-gold-transformation-layer.md)). This row and the 3 other planned Gold notebooks (`nb_gold_fact_telemetry_v1`, `nb_gold_health_score_v1`, `nb_gold_sla_metrics_v1`) never existed as real artifacts — the marts exist as placeholder stub `.sql` files instead |

## 4. RBAC Role Assignments

| Principal | Workspace Role | Scope | Notes |
|---|---|---|---|
| `sp-fabric-mal` | Admin | `ModernAnalyticsLab-DEV`, `ModernAnalyticsLab-Sandbox` | Platform service principal — capacity & workspace administration |
| `sp-ironwatch-dev` | Member | `ModernAnalyticsLab-DEV` | Pipeline service principal — runs Copy Activity pipelines and dbt-fabric, writes Bronze/Silver/Gold |
| Data engineering team | Contributor | `ModernAnalyticsLab-DEV` | Builds and edits notebooks, semantic model, pipelines |
| Analytics / BI consumers | Viewer | `ModernAnalyticsLab-DEV` (demo state only) | Read-only access to the published semantic model and reports |
| Data engineering team | Admin | `ModernAnalyticsLab-Sandbox` | Full control for exploratory work; isolated from DEV |

Secrets for all service principals are referenced via the
`mal-kv-shared` Key Vault (`rg-shared-infra`) — never stored in workspace
items or `.env` files.

## 5. Git Branch Strategy

```
main      ─────●───────────────●────────────●──────  (demo-ready snapshots)
                \             /            /
develop    ──●───●───●───●───●───●───●───●────────  (active build)
              \   \       \
feature/*      ●   ●       ●                          (short-lived work branches)
```

| Branch | Purpose |
|---|---|
| `develop` | Active build branch — all day-to-day pipeline, schema, and dbt model changes land here first |
| `main` | Demo-ready branch — only merged from `develop` when the workspace is in a stable, presentable state for stakeholder demos |
| `feature/*` | Optional short-lived branches for larger changes, merged back into `develop` |

Promotion flow: `feature/*` → `develop` → `main`. Never commit directly to `main`.

## 6. OneLake Folder Structure

```
ModernAnalyticsLab-DEV.Workspace/
└── OneLake/
    ├── ironwatch_bronze.Lakehouse/
    │   └── Files/
    │       ├── telemetry/
    │       ├── oil_samples/
    │       ├── fault_codes/
    │       ├── asset_master/
    │       └── service_history/
    │   └── Tables/
    │       ├── telemetry_raw
    │       ├── oil_samples_raw
    │       ├── fault_codes_raw
    │       ├── asset_master_raw
    │       └── service_history_raw
    │
    ├── ironwatch_silver.Warehouse/  # re-provisioned 2026-07-18 per ADR-010
    │   └── Tables/
    │       ├── telemetry
    │       ├── oil_samples
    │       ├── fault_codes
    │       ├── asset_master
    │       └── service_history
    │
    └── ironwatch_gold.Warehouse/
        └── Tables/
            ├── dim_asset
            ├── dim_date
            ├── fact_telemetry
            ├── fact_health_score
            └── fact_sla_metrics
```

`Files/` paths under `ironwatch_bronze` mirror the drop-zone structure
produced by the synthetic generators (`synthetic_data/output/`) per
[ADR-002](ADR/ADR-002-bronze-sources.md).

## 7. Open Decisions

**None — all Phase 2 decisions are resolved.**

---

Last updated: 2026-06-07 (amended 2026-07-18 per ADR-010, executed same day — §2/§3/§6 Silver rows only) | Status: FINAL — do not modify during build
