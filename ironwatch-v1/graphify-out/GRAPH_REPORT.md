# Graph Report - .  (2026-07-26)

## Corpus Check
- Corpus is ~17,658 words - fits in a single context window. You may not need a graph.

## Summary
- 148 nodes · 240 edges · 20 communities (19 shown, 1 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.88)
- Token cost: 0 input · 135,973 output

## Community Hubs (Navigation)
- Data Model & Health Score
- Audit & dbt Execution
- Identity & Resource Placement
- Pipeline Configuration
- Solution Architecture & README
- Synthetic Data Generation
- Bronze Pipeline Builder
- ADO Backlog Import
- Bronze/Silver Source Mapping
- ADR Index (Gold/Telemetry/Spark-Free)
- Agent Prompts & Query Agent
- Workspace Design & Access Boundaries
- dbt Gold Project Config
- IronCore Framework (proposed)

## God Nodes (most connected - your core abstractions)
1. `ADR-010: Silver as Warehouse, dbt-fabric Spans Silver-Gold` - 14 edges
2. `IronWatch v1 Solution Architecture` - 12 edges
3. `IronWatch v1 Data Model Reference` - 12 edges
4. `ADR-009: dbt-fabric as Gold Transformation Layer` - 11 edges
5. `IronWatch v1 Workspace Design` - 10 edges
6. `ADR-001: Gold Layer as Fabric Warehouse` - 9 edges
7. `OREXA Heavy Industries Synthetic Data Spec` - 9 edges
8. `log_execution()` - 8 edges
9. `main()` - 8 edges
10. `ADR-007: Spark-Free Compute Architecture` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Off-limits paths for agents (.venv/, notebooks/, synthetic_data/, scripts/infra/)` --semantically_similar_to--> `Notebook Naming Convention (§3, all rows superseded)`  [INFERRED] [semantically similar]
  AGENTS.md → docs/WORKSPACE_DESIGN.md
- `Audit & Observability (execution_log)` --semantically_similar_to--> `Audit & Execution Logging (§6)`  [INFERRED] [semantically similar]
  README.md → docs/ARCHITECTURE.md
- `CI/CD & Review Workflow (ship/ship-status)` --semantically_similar_to--> `CI/CD & Review Workflow (§7)`  [INFERRED] [semantically similar]
  README.md → docs/ARCHITECTURE.md
- `ADR-004: Identity Model` --references--> `mal-automation shared identity`  [EXTRACTED]
  docs/ADR/ADR-004-identity-model.md → CLAUDE.md
- `ADR-004: Identity Model` --references--> `sp-fabric-mal service principal`  [EXTRACTED]
  docs/ADR/ADR-004-identity-model.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Medallion pipeline flow (Bronze -> Silver -> Gold)** — readme_medallion_pipeline, docs_architecture_medallion_diagram, docs_data_model_bronze_inventory, docs_data_model_silver_dq_rules, docs_data_model_gold_star_schema [INFERRED 0.85]
- **Storage-engine decision chain (Gold Warehouse -> Spark-free -> dbt-fabric Gold -> Silver Warehouse)** — docs_adr_adr_001_gold_warehouse_decision, docs_adr_adr_007_spark_free_architecture_decision, docs_adr_adr_009_dbt_gold_transformation_layer_decision, docs_adr_adr_010_silver_warehouse_dbt_scope_decision [EXTRACTED 1.00]
- **Identity and secrets model (service principals + Key Vault)** — claude_mal_kv_shared, claude_sp_fabric_mal, claude_sp_ironwatch_dev, claude_mal_automation, docs_adr_adr_004_identity_model_decision [EXTRACTED 1.00]

## Communities (20 total, 1 thin omitted)

### Community 0 - "Data Model & Health Score"
Cohesion: 0.11
Nodes (25): Decision: Gold provisioned as Fabric Warehouse, not Lakehouse, ADR-005: OREXA Entity Model Adopted, Decision: adopt OREXA Heavy Industries entity model for synthetic data, ADR-008: Calendar-Time Join and Health Score Redesign, Decision: calendar-time join + calendar-days-since-service health score term (reject hours_operated), Redesigned Health Score formula (fault penalty + oil verdict penalty + days-since-service term), dbt-fabric adapter, Open Decisions Log (+17 more)

### Community 1 - "Audit & dbt Execution"
Cohesion: 0.20
Nodes (14): _active_spark_session(), _audit_table_path(), log_execution(), Delta-backed execution audit log for IronWatch v1 pipelines.  Every notebook c, Record one pipeline execution event and return its run_id.      Always returns, _write_with_pandas(), _write_with_spark(), main() (+6 more)

### Community 2 - "Identity & Resource Placement"
Cohesion: 0.19
Nodes (14): mal-automation shared identity, mal-kv-shared Key Vault, IronWatch naming convention, rg-fabric-sandbox resource group, rg-ironwatch-dev resource group (unused), sp-fabric-mal service principal, sp-ironwatch-dev service principal, ADR-003: Resource Group Placement (+6 more)

### Community 3 - "Pipeline Configuration"
Cohesion: 0.27
Nodes (10): Exception, ConfigurationError, get_config(), get_lakehouse_path(), Single source of truth for IronWatch v1 environment configuration.  Every notebo, Return the abfss:// OneLake path for the given medallion layer.      `layer` mus, Raised when required IronWatch configuration is missing or invalid., Resolve and return all workspace-level settings as a WorkspaceConfig. (+2 more)

### Community 4 - "Solution Architecture & README"
Cohesion: 0.20
Nodes (10): IronWatch v1 Solution Architecture, Audit & Execution Logging (§6), CI/CD & Review Workflow (§7), Medallion architecture overview diagram, V2 Extension Points (Eventhouse/RTI, Fabric Data Agent MCP, Ontology MCP, Snowflake Iceberg, dbt Core), Audit & Observability (execution_log), CI/CD & Review Workflow (ship/ship-status), IronWatch v1 project (+2 more)

### Community 5 - "Synthetic Data Generation"
Cohesion: 0.38
Nodes (10): generate_asset_master(), generate_fault_codes(), generate_oil_samples(), generate_service_history(), generate_telemetry(), load_config(), main(), make_assets() (+2 more)

### Community 6 - "Bronze Pipeline Builder"
Cohesion: 0.39
Nodes (8): build_pipeline_content(), create_pipeline_item(), main(), poll_job(), Create, run, and verify the Bronze ingestion Data Pipelines (ADR-002/ADR-007)., run_pipeline(), _source_type_properties(), _token()

### Community 7 - "ADO Backlog Import"
Cohesion: 0.39
Nodes (8): _cli_safe(), create_work_item(), link_parent(), main(), Import docs/azure-boards/ironwatch_v1_v2_backlog.csv into Azure Boards via az CL, Side-effect-free preflight so a bad row can't leave earlier rows'     work item, run_az(), _validate_rows()

### Community 8 - "Bronze/Silver Source Mapping"
Cohesion: 0.29
Nodes (8): ADR-002: Bronze Sources Are Flat-File Drops, Decision: ADLS Gen2 flat-file drops as Bronze source, simulated by generators, ADR-010: Silver as Warehouse, dbt-fabric Spans Silver-Gold, Audit table contract: single _ironwatch_meta/execution_log hosted in Bronze, Decision: convert Silver to Fabric Warehouse, extend dbt-fabric to span Silver+Gold, sources.yml migration: silver source removed, bronze source added, ironwatch_gold models/staging/sources.yml, bronze source block (5 raw tables)

### Community 9 - "ADR Index (Gold/Telemetry/Spark-Free)"
Cohesion: 0.33
Nodes (6): ADR-001: Gold Layer as Fabric Warehouse, Snowflake external tables over OneLake (Iceberg) - rejected alternative, ADR-006: Telemetry Fields Standardized to Metric Units, Decision: standardize telemetry fields to metric units (hydraulic_pressure_bar replaces oil_pressure_psi), ADR-007: Spark-Free Compute Architecture, Decision: Bronze/Silver/Gold all avoid Spark compute (Copy Activity / Dataflow Gen2 / T-SQL)

### Community 10 - "Agent Prompts & Query Agent"
Cohesion: 0.40
Nodes (4): IronWatchQueryAgent (forward-looking, undefined), Prompt 9 plan-approve gate, Prompt 9 status: empty, no numbered prompt files exist, Numbered prompt-spec convention (NN-short-slug.md)

### Community 11 - "Workspace Design & Access Boundaries"
Cohesion: 0.33
Nodes (6): Off-limits paths for agents (.venv/, notebooks/, synthetic_data/, scripts/infra/), IronWatch v1 Workspace Design, Git Branch Strategy (§5, feature/*->develop->main), Fabric Item Inventory (§2), Notebook Naming Convention (§3, all rows superseded), RBAC Role Assignments (§4)

### Community 12 - "dbt Gold Project Config"
Cohesion: 0.67
Nodes (4): ADR-009: dbt-fabric as Gold Transformation Layer, Decision: adopt dbt-fabric as Gold transformation layer, replacing T-SQL stored procs/views, ironwatch_gold dbt_project.yml, dbt project config (staging=view, marts=table)

## Knowledge Gaps
- **25 isolated node(s):** `IronWatchQueryAgent (forward-looking, undefined)`, `rg-fabric-sandbox resource group`, `rg-ironwatch-dev resource group (unused)`, `IronWatch naming convention`, `IronWatch v1 project` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ADR-010: Silver as Warehouse, dbt-fabric Spans Silver-Gold` connect `Bronze/Silver Source Mapping` to `Data Model & Health Score`, `Identity & Resource Placement`, `Solution Architecture & README`, `ADR Index (Gold/Telemetry/Spark-Free)`, `Agent Prompts & Query Agent`, `Workspace Design & Access Boundaries`, `dbt Gold Project Config`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `IronWatch v1 Solution Architecture` connect `Solution Architecture & README` to `Identity & Resource Placement`, `Bronze/Silver Source Mapping`, `ADR Index (Gold/Telemetry/Spark-Free)`, `Agent Prompts & Query Agent`, `dbt Gold Project Config`, `IronCore Framework (proposed)`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `IronWatch v1 Data Model Reference` connect `Data Model & Health Score` to `ADR Index (Gold/Telemetry/Spark-Free)`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **What connects `IronWatchQueryAgent (forward-looking, undefined)`, `rg-fabric-sandbox resource group`, `rg-ironwatch-dev resource group (unused)` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Data Model & Health Score` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._