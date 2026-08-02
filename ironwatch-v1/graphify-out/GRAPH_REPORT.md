# Graph Report - .  (2026-08-01)

## Corpus Check
- Corpus is ~18,289 words - fits in a single context window. You may not need a graph.

## Summary
- 194 nodes · 275 edges · 25 communities (16 shown, 9 thin omitted)
- Extraction: 86% EXTRACTED · 13% INFERRED · 1% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.88)
- Token cost: 0 input · 52,090 output

## Community Hubs (Navigation)
- ADR Decisions & Agent Conventions
- Architecture Overview
- Ops & Semantic Model
- OREXA Data Model
- Infra Audit Script
- OREXA Spec & dbt Project Config
- Fault-Event Gap & Synthetic Data Gen
- Infra Config Script
- Bronze Pipeline Builder
- ADO Backlog Importer
- Project Identity
- Graphify Integration
- Naming Convention
- Prompt 9 Query Agent Gate
- Ship / CI-CD Workflow
- Doc Index & Prompt Conventions
- IronWatch Agent Entry
- Off-Limits Paths
- Project Structure
- Quickstart Guide

## God Nodes (most connected - your core abstractions)
1. `ADR-010: Silver as Warehouse, dbt-fabric Spans Silver→Gold` - 11 edges
2. `ADR Quick Reference Table` - 10 edges
3. `ADR-007: Spark-Free Compute Architecture` - 10 edges
4. `ADR-009: dbt-fabric as Gold Transformation Layer` - 9 edges
5. `log_execution()` - 8 edges
6. `main()` - 8 edges
7. `IronWatch v1 — Solution Architecture` - 8 edges
8. `Medallion Architecture (Bronze/Silver/Gold)` - 8 edges
9. `Bronze Source File Inventory` - 8 edges
10. `fact_equipment_health` - 8 edges

## Surprising Connections (you probably didn't know these)
- `OPEN-002: No Per-Asset Fault-Event Stream Exists in Bronze` --references--> `generate_fault_codes()`  [INFERRED]
  docs/ADR/OPEN_DECISIONS.md → synthetic_data/generators/generate_all.py
- `IronWatch v1 Project Description` --semantically_similar_to--> `IronWatch v1 Overview`  [INFERRED] [semantically similar]
  CLAUDE.md → README.md
- `OPEN-002: No Per-Asset Fault-Event Stream Exists in Bronze` --references--> `generate_telemetry()`  [EXTRACTED]
  docs/ADR/OPEN_DECISIONS.md → synthetic_data/generators/generate_all.py
- `mal-kv-shared Key Vault` --shares_data_with--> `ADR-004: Identity Model`  [INFERRED]
  CLAUDE.md → docs/ADR/ADR-004-identity-model.md
- `Service Principals (sp-fabric-mal, sp-ironwatch-dev, mal-automation)` --shares_data_with--> `ADR-004: Identity Model`  [INFERRED]
  CLAUDE.md → docs/ADR/ADR-004-identity-model.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **IronWatch Key Vault / Service Principal Auth Chain** — claude_key_vault_mal_kv_shared, claude_service_principals, docs_adr_adr_004_identity_model_decision, docs_adr_adr_009_dbt_gold_transformation_layer_decision, docs_adr_adr_010_silver_warehouse_dbt_scope_decision [INFERRED 0.85]
- **Medallion Architecture Pipeline (Bronze→Silver→Gold)** — docs_adr_adr_002_bronze_sources_decision, docs_adr_adr_007_spark_free_architecture_decision, docs_adr_adr_010_silver_warehouse_dbt_scope_decision, docs_adr_adr_001_gold_warehouse_decision, docs_adr_adr_009_dbt_gold_transformation_layer_decision [INFERRED 0.85]
- **Recurring 'Flagged for Follow-Up, Not Fixed Here' Documentation Staleness Pattern** — docs_adr_adr_003_resource_group_placement_decision, docs_adr_adr_005_orexa_entity_model_decision, docs_adr_adr_007_spark_free_architecture_decision, docs_adr_adr_010_silver_warehouse_dbt_scope_decision [INFERRED 0.85]
- **Silver Lakehouse-to-Warehouse Migration (ADR-010)** — docs_architecture_ironwatch_silver, docs_workspace_design_fabric_item_inventory, transform_ironwatch_gold_profiles_silver_target, transform_ironwatch_gold_models_staging_sources [INFERRED 0.85]
- **OREXA Bronze Source Mapping (Spec → Data Model → Architecture → dbt Source)** — docs_orexa_spec_pulsenet, docs_data_model_bronze_source_inventory, docs_architecture_ironwatch_bronze, transform_ironwatch_gold_models_staging_sources_bronze [INFERRED 0.85]
- **Gold Star Schema Health-Scoring Pipeline** — docs_data_model_gold_star_schema, docs_data_model_fact_equipment_health, docs_data_model_health_score_formula, docs_data_model_dax_measure_stubs [INFERRED 0.85]
- **Silver Fault-Side Build Blocked by Missing Fault-Event Stream** — docs_adr_open_decisions_open_002, docs_adr_open_decisions_stg_fault_aggregations, docs_adr_open_decisions_int_iw_fault_aggregations, synthetic_data_generators_generate_all [INFERRED 0.80]

## Communities (25 total, 9 thin omitted)

### Community 0 - "ADR Decisions & Agent Conventions"
Cohesion: 0.08
Nodes (39): ironwatch_bronze Lakehouse, dbt-fabric, ironwatch_gold Warehouse, OREXA Domain Conventions, ironwatch_silver Warehouse, Environment Configuration, mal-kv-shared Key Vault, Service Principals (sp-fabric-mal, sp-ironwatch-dev, mal-automation) (+31 more)

### Community 1 - "Architecture Overview"
Cohesion: 0.11
Nodes (26): IronWatch v1 — Solution Architecture, scripts/infra/audit.py, scripts/infra/build_bronze_pipelines.py, scripts/infra/config.py, V2 Extension: dbt Core (Decided for v1), Silver dbt Model — Infrastructure Ready, Not Yet Written, V2 Extension: Eventhouse / Real-Time Intelligence, _ironwatch_meta/execution_log Audit Table (+18 more)

### Community 2 - "Ops & Semantic Model"
Cohesion: 0.17
Nodes (16): Azure Infrastructure (rg-fabric-sandbox / rg-shared-infra / rg-ironwatch-dev), CI/CD & Review Workflow (CodeRabbit), Power BI Semantic Model (DirectLake), /ship command, /ship-status command, Power BI DAX Measure Stubs, dim_asset, dim_date (+8 more)

### Community 3 - "OREXA Data Model"
Cohesion: 0.16
Nodes (16): Python Generators (Ingestion Layer), IronWatch v1 — Data Model Reference, Bronze Source File Inventory, Known Gap: fault_codes.json Is a Catalog, Not a Fault-Event Stream, HealthScore Formula, Same-Calendar-Day Oil-Sample/Telemetry Join, silver_asset_registry, Silver DQ Rules (+8 more)

### Community 4 - "Infra Audit Script"
Cohesion: 0.20
Nodes (14): _active_spark_session(), _audit_table_path(), log_execution(), Delta-backed execution audit log for IronWatch v1 pipelines.  Every notebook c, Record one pipeline execution event and return its run_id.      Always returns, _write_with_pandas(), _write_with_spark(), main() (+6 more)

### Community 5 - "OREXA Spec & dbt Project Config"
Cohesion: 0.20
Nodes (13): Gold Mart Models (fact_telemetry, fact_health_score), Asset Registry, Ironback (Graders), Kestrel (Excavators), PulseNet (Telemetry Subsystem), Titan (Haul Trucks), ironwatch_gold dbt_project.yml, marts models config (materialized=table) (+5 more)

### Community 6 - "Fault-Event Gap & Synthetic Data Gen"
Cohesion: 0.30
Nodes (13): int_iw_fault_aggregations, OPEN-002: No Per-Asset Fault-Event Stream Exists in Bronze, stg_fault_aggregations, generate_asset_master(), generate_fault_codes(), generate_oil_samples(), generate_service_history(), generate_telemetry() (+5 more)

### Community 7 - "Infra Config Script"
Cohesion: 0.27
Nodes (10): Exception, ConfigurationError, get_config(), get_lakehouse_path(), Single source of truth for IronWatch v1 environment configuration.  Every note, Return the abfss:// OneLake path for the given medallion layer.      `layer` m, Raised when required IronWatch configuration is missing or invalid., Resolve and return all workspace-level settings as a WorkspaceConfig. (+2 more)

### Community 8 - "Bronze Pipeline Builder"
Cohesion: 0.39
Nodes (8): build_pipeline_content(), create_pipeline_item(), main(), poll_job(), Create, run, and verify the Bronze ingestion Data Pipelines (ADR-002/ADR-007)., run_pipeline(), _source_type_properties(), _token()

### Community 9 - "ADO Backlog Importer"
Cohesion: 0.39
Nodes (8): _cli_safe(), create_work_item(), link_parent(), main(), Import docs/azure-boards/ironwatch_v1_v2_backlog.csv into Azure Boards via az CL, Side-effect-free preflight so a bad row can't leave earlier rows'     work item, run_az(), _validate_rows()

### Community 10 - "Project Identity"
Cohesion: 0.67
Nodes (3): IronWatch v1 Project Description, IronCore Framework Extraction (IronWatch v2), IronWatch v1 Overview

## Ambiguous Edges - Review These
- `stg_equipment.sql` → `stg_telemetry.sql`  [AMBIGUOUS]
  transform/ironwatch_gold/models/staging/stg_telemetry.yml · relation: conceptually_related_to
- `fact_equipment_health` → `OneLake Folder Structure`  [AMBIGUOUS]
  docs/WORKSPACE_DESIGN.md · relation: conceptually_related_to

## Knowledge Gaps
- **43 isolated node(s):** `IronWatch v1 (Agent Orientation)`, `ironwatch_bronze Lakehouse`, `OREXA Domain Conventions`, `Prompt 9 / IronWatchQueryAgent Plan-Approve Gate (undefined)`, `/ship /ship-status Process` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `stg_equipment.sql` and `stg_telemetry.sql`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `fact_equipment_health` and `OneLake Folder Structure`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Bronze Source File Inventory` connect `OREXA Data Model` to `OREXA Spec & dbt Project Config`, `Fault-Event Gap & Synthetic Data Gen`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `OPEN-002: No Per-Asset Fault-Event Stream Exists in Bronze` connect `Fault-Event Gap & Synthetic Data Gen` to `OREXA Data Model`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `Medallion Architecture (Bronze/Silver/Gold)` connect `Architecture Overview` to `Ops & Semantic Model`, `OREXA Data Model`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **What connects `IronWatch v1 (Agent Orientation)`, `ironwatch_bronze Lakehouse`, `OREXA Domain Conventions` to the rest of the system?**
  _43 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ADR Decisions & Agent Conventions` be split into smaller, more focused modules?**
  _Cohesion score 0.07557354925775979 - nodes in this community are weakly interconnected._