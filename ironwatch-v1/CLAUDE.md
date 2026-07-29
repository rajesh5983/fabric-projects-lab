PROJECT: IronWatch v1
DESCRIPTION: Predictive equipment health intelligence platform built on
Microsoft Fabric. Medallion architecture (bronze/silver/gold) with synthetic
OREXA Heavy Industries telemetry, oil sample, fault code, asset master, and
service history data (see docs/OREXA_SPEC.md). Target: demoable Power BI
semantic model by June 30 2026.

ENVIRONMENT:
- Platform: Windows + VS Code + Claude Code CLI
- Fabric: F2 SKU (fabricf2sandbox) in ModernAnalyticsLab tenant
- Azure subscription: ModernAnalyticsLab
- Key Vault: mal-kv-shared in rg-shared-infra
- Service principals: sp-fabric-mal (platform), sp-ironwatch-dev (pipeline);
  mal-automation (shared tenant automation identity — holds Key Vault Secrets
  User on mal-kv-shared; not project-specific, do not reassign or remove it)
- Resource group: rg-fabric-sandbox — actual home of the F2 capacity
  (fabricf2sandbox) and landing storage (fabricf2landingsa). rg-ironwatch-dev
  exists but is empty and not in active use for this project (confirmed via
  audit 2026-06-20).

NAMING CONVENTION:
- Workspaces: ModernAnalyticsLab-DEV, ModernAnalyticsLab-Sandbox
- Lakehouse: ironwatch_bronze (only Bronze is a Lakehouse)
- Warehouses: ironwatch_silver, ironwatch_gold (Fabric Warehouses — silver
  re-provisioned from Lakehouse 2026-07-18, see ADR-010; gold see ADR-001)
- Notebooks: nb_[layer]_[purpose]_[version] e.g. nb_bronze_telemetry_v1
- Files: [project]_[layer]_[object]_[env] e.g. ironwatch_bronze_telemetry_dev

NEVER: hardcode credentials, commit .env files, name Gold or Silver layers
as a Lakehouse, name Bronze as a Warehouse.

ALWAYS: reference secrets via mal-kv-shared Key Vault, follow naming
convention above, document decisions in docs/ADR/.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
