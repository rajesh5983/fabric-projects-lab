# IronWatch v1 — Claude Code Context

## Project Overview
IronWatch v1 is a predictive equipment health intelligence platform built on Microsoft Fabric.
It ingests synthetic CAT-style machine telemetry through a medallion architecture (bronze → silver → gold Warehouse)
and surfaces insights via a Power BI semantic model.

## Key Directories
- `synthetic_data/generators/` — Python scripts that produce synthetic telemetry CSV/JSON
- `synthetic_data/schemas/` — JSON Schema definitions for each telemetry event type
- `synthetic_data/output/` — Generated files (gitignored except .gitkeep)
- `notebooks/bronze/` — Fabric Notebooks: raw ingestion into Bronze Lakehouse/Warehouse
- `notebooks/silver/` — Fabric Notebooks: cleansing, deduplication, type alignment
- `notebooks/gold/` — Fabric Notebooks: aggregations, SLA metrics, health-score computation
- `semantic_model/` — Power BI semantic model TMDL or BIM files
- `docs/` — Architecture, data model, and ADR documents
- `scripts/infra/` — Terraform / Bicep / PowerShell infra automation

## Architecture Decisions
See `docs/ADR/` for all Architecture Decision Records.
- ADR-001: Gold layer uses Fabric Warehouse (SQL endpoint), not Lakehouse delta tables
- ADR-002: Bronze sources are flat-file drops (ADLS Gen2) simulated by synthetic generators

## Environment
Copy `.env.template` → `.env` and fill in workspace / connection strings before running notebooks.
Never commit `.env`.

## Coding Conventions
- Notebook cells: PySpark unless otherwise noted
- Schema validation in Bronze notebooks before writing to Silver
- All Gold tables must have a `_loaded_utc` watermark column
- Semantic model measures use DAX; no calculated columns in the model layer
