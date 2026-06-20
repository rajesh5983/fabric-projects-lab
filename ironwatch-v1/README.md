# IronWatch v1

Predictive equipment health intelligence platform built on Microsoft Fabric.

## What It Does
IronWatch ingests synthetic OREXA Heavy Industries equipment telemetry (Titan haul trucks, Kestrel
excavators, Ironback graders — see docs/OREXA_SPEC.md) through a three-layer medallion pipeline,
computes health scores and maintenance SLA metrics, and exposes a Power BI semantic model for dashboards
and predictive alerting.

## Architecture at a Glance

```
Synthetic Generators
        │  CSV / JSON / Parquet drop
        ▼
  Bronze Lakehouse        ← raw, schema-validated, append-only (Data Pipeline Copy Activity)
        │  Dataflow Gen2 cleanse
        ▼
  Silver Lakehouse        ← deduplicated, typed, partitioned by asset_id / date
        │  Dataflow Gen2 aggregate
        ▼
  Gold Warehouse          ← SQL endpoint, health-score facts, dimension tables (T-SQL)
        │  DirectLake / Import
        ▼
  Power BI Semantic Model ← DAX measures, RLS, composite model
```
Spark-free end-to-end — see [ADR-007](docs/ADR/ADR-007-spark-free-architecture.md).

## Quickstart

```bash
# 1. Set up environment
cp .env.template .env
# fill in FABRIC_WORKSPACE_ID, ADLS_ACCOUNT_NAME, etc.

# 2. Generate synthetic telemetry
cd synthetic_data/generators
python generate_telemetry.py --machines 50 --days 90 --out ../output

# 3. Run notebooks in order
#    bronze/ → silver/ → gold/
#    Upload and execute via Fabric UI or Fabric REST API

# 4. Deploy semantic model
cd semantic_model
# follow docs/WORKSPACE_DESIGN.md for deployment steps
```

## Project Structure

```
ironwatch-v1/
├── CLAUDE.md                  # Claude Code context
├── .env.template              # Environment variable template
├── docs/
│   ├── WORKSPACE_DESIGN.md    # Fabric workspace layout & naming
│   ├── ARCHITECTURE.md        # Full solution architecture
│   ├── DATA_MODEL.md          # Bronze/Silver/Gold schema reference
│   └── ADR/                   # Architecture Decision Records
├── synthetic_data/
│   ├── generators/            # Python telemetry generators
│   ├── schemas/               # JSON Schema definitions
│   └── output/                # Generated files (gitignored)
├── notebooks/
│   ├── bronze/                # Raw ingestion notebooks
│   ├── silver/                # Cleansing notebooks
│   └── gold/                  # Aggregation & scoring notebooks
├── semantic_model/            # Power BI TMDL / BIM files
└── scripts/infra/             # Terraform / Bicep / PS automation
```

## Tech Stack
| Layer | Technology |
|---|---|
| Bronze compute | Data Pipeline Copy Activity (no Spark — ADR-007) |
| Silver compute | Dataflow Gen2 (Power Query engine, no Spark — ADR-007) |
| Gold compute | Fabric Warehouse, T-SQL stored procedures/views (ADR-001) |
| Bronze / Silver storage | Fabric Lakehouse (Delta Lake) |
| Gold storage | Fabric Warehouse (SQL endpoint) |
| Orchestration | Fabric Data Factory pipelines |
| Semantic layer | Power BI semantic model (DirectLake) |
| Synthetic data | Python + Faker |
| IaC | Bicep + PowerShell |

## Status
Scaffolded June 2026 — synthetic data generation and bronze notebooks in progress.
