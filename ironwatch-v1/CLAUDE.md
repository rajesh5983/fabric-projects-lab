PROJECT: IronWatch v1
DESCRIPTION: Predictive equipment health intelligence platform built on
Microsoft Fabric. Medallion architecture (bronze/silver/gold) with synthetic
CAT-style telemetry, oil sample, fault code, asset master, and service
history data. Target: demoable Power BI semantic model by June 30 2026.

ENVIRONMENT:
- Platform: Windows + VS Code + Claude Code CLI
- Fabric: F2 SKU (fabricf2sandbox) in ModernAnalyticsLab tenant
- Azure subscription: ModernAnalyticsLab
- Key Vault: mal-kv-shared in rg-shared-infra
- Service principals: sp-fabric-mal (platform), sp-ironwatch-dev (pipeline)
- Resource group: rg-ironwatch-dev

NAMING CONVENTION:
- Workspaces: ModernAnalyticsLab-DEV, ModernAnalyticsLab-Sandbox
- Lakehouses: ironwatch_bronze, ironwatch_silver (both Lakehouses)
- Warehouse: ironwatch_gold (Fabric Warehouse — see ADR-001)
- Notebooks: nb_[layer]_[purpose]_[version] e.g. nb_bronze_telemetry_v1
- Files: [project]_[layer]_[object]_[env] e.g. ironwatch_bronze_telemetry_dev

NEVER: hardcode credentials, commit .env files, use rg-fabric-sandbox
for IronWatch resources, name Gold layer as a Lakehouse.

ALWAYS: reference secrets via mal-kv-shared Key Vault, follow naming
convention above, document decisions in docs/ADR/.
