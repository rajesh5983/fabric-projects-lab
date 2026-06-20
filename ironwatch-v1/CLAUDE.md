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
- Lakehouses: ironwatch_bronze, ironwatch_silver (both Lakehouses)
- Warehouse: ironwatch_gold (Fabric Warehouse — see ADR-001)
- Notebooks: nb_[layer]_[purpose]_[version] e.g. nb_bronze_telemetry_v1
- Files: [project]_[layer]_[object]_[env] e.g. ironwatch_bronze_telemetry_dev

NEVER: hardcode credentials, commit .env files, name Gold layer as a
Lakehouse.

ALWAYS: reference secrets via mal-kv-shared Key Vault, follow naming
convention above, document decisions in docs/ADR/.
