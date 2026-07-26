# IronWatch v1 — Documentation Index

Map of existing docs. This file only indexes; it doesn't move, rename, or
restate content — follow the links.

| Doc | Purpose |
|---|---|
| [`../README.md`](../README.md) | Project overview, quickstart, tech stack table |
| [`../AGENTS.md`](../AGENTS.md) | Short stable-fact orientation for coding agents |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Full solution architecture: medallion layers, data flow narrative, v2 extension points, Azure infra, audit logging, CI/CD workflow |
| [`DATA_MODEL.md`](DATA_MODEL.md) | Bronze source inventory, Silver DQ rules, oil-sample temporal join, Gold star schema, health-score formula, DAX measure stubs |
| [`OREXA_SPEC.md`](OREXA_SPEC.md) | OREXA Heavy Industries synthetic data spec: equipment lines, sites, subsystem file mapping, fault code taxonomy |
| [`WORKSPACE_DESIGN.md`](WORKSPACE_DESIGN.md) | Fabric workspace layout, item inventory, naming, RBAC, branch strategy, OneLake folder structure |
| [`ADR/`](ADR/) | Architecture Decision Records (ADR-001 through ADR-010) — numbered, chronological, final once merged |
| [`ADR/OPEN_DECISIONS.md`](ADR/OPEN_DECISIONS.md) | Unresolved design questions awaiting a decision, promoted to a numbered ADR once resolved |
| [`azure-boards/`](azure-boards/) | Exported backlog (CSV) — v1/v2 epics and user stories |
| [`03-prompts/`](03-prompts/) | Numbered agent prompt specs (see its README for the convention) |

## ADR quick reference

| ADR | Decision |
|---|---|
| [001](ADR/ADR-001-gold-warehouse.md) | Gold is a Fabric Warehouse, not a Lakehouse |
| [002](ADR/ADR-002-bronze-sources.md) | Bronze source ingestion approach |
| [003](ADR/ADR-003-resource-group-placement.md) | Resource group placement (`rg-fabric-sandbox` vs `rg-ironwatch-dev`) |
| [004](ADR/ADR-004-identity-model.md) | Service principal / identity model |
| [005](ADR/ADR-005-orexa-entity-model.md) | OREXA entity model |
| [006](ADR/ADR-006-telemetry-unit-standardization.md) | Telemetry unit standardization |
| [007](ADR/ADR-007-spark-free-architecture.md) | Spark-free architecture (Copy Activity + dbt-fabric, no notebooks) |
| [008](ADR/ADR-008-utilization-and-health-score-redesign.md) | Utilization tracking & health-score formula redesign |
| [009](ADR/ADR-009-dbt-gold-transformation-layer.md) | dbt-fabric as the Gold transformation layer |
| [010](ADR/ADR-010-silver-warehouse-dbt-scope.md) | Silver re-provisioned as a Warehouse, scoped into the same dbt project |
