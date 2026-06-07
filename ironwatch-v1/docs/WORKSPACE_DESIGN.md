# IronWatch v1 — Fabric Workspace Design

## Workspace Layout

| Item | Type | Purpose |
|---|---|---|
| `ironwatch-bronze` | Lakehouse | Raw telemetry drop zone, schema-validated Delta tables |
| `ironwatch-silver` | Lakehouse | Cleansed, deduplicated, partitioned Delta tables |
| `ironwatch-gold` | Warehouse | Aggregated facts + dimensions, SQL endpoint for semantic model |
| `ironwatch-pipelines` | Data Factory | Orchestration: generator → bronze → silver → gold |
| `ironwatch-semantic` | Semantic Model | Power BI DirectLake model over Gold Warehouse |
| `ironwatch-dashboard` | Report | Operational equipment health dashboard |

## Naming Conventions

- **Tables**: `snake_case`, singular nouns (e.g. `machine`, `telemetry_event`)
- **Gold fact tables**: prefix `fact_` (e.g. `fact_equipment_health`)
- **Gold dimension tables**: prefix `dim_` (e.g. `dim_machine`, `dim_date`)
- **Notebooks**: `<layer>_<verb>_<subject>.ipynb` (e.g. `bronze_ingest_telemetry.ipynb`)
- **Pipelines**: `pl_<layer>_<subject>` (e.g. `pl_bronze_telemetry_load`)

## Environment Tiers

| Tier | Workspace Suffix | Branch |
|---|---|---|
| Development | `-dev` | feature/* |
| Staging | `-stg` | main |
| Production | `-prod` | releases/* |

## Capacity & SKU
Target: **F2** SKU (smallest paid Fabric capacity) for dev/stg.
Production sizing TBD based on telemetry volume and query concurrency requirements.

## Access Control
- Workspace Admin: platform team service principal
- Contributor: data engineering team
- Viewer: analytics / BI consumers
- RLS enforced in semantic model for site-level data partitioning
