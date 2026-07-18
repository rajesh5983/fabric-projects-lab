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
        │  dbt-fabric model (source: Bronze)
        ▼
  Silver Warehouse        ← deduplicated, typed, SQL endpoint (dbt-fabric)
        │  dbt-fabric model (ref: Silver)
        ▼
  Gold Warehouse          ← SQL endpoint, health-score facts, dimension tables (dbt-fabric)
        │  DirectLake / Import
        ▼
  Power BI Semantic Model ← DAX measures, RLS, composite model
```
Spark-free end-to-end — see [ADR-007](docs/ADR/ADR-007-spark-free-architecture.md).
Silver and Gold are both built by a single `dbt-fabric` project
(`transform/ironwatch_gold/`) — see [ADR-009](docs/ADR/ADR-009-dbt-gold-transformation-layer.md)
(Gold) and [ADR-010](docs/ADR/ADR-010-silver-warehouse-dbt-scope.md) (Silver).
Silver's own model files aren't written yet — infrastructure (Warehouse,
`sources.yml`, dbt target) is live, transformation logic is next session's
task.

## Quickstart

```bash
# 1. Set up environment
cp .env.template .env
# Fill in AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, FABRIC_WORKSPACE_DEV,
# IRONWATCH_GOLD_SQL_ENDPOINT, IRONWATCH_SILVER_SQL_ENDPOINT, etc. — see
# .env.template for the full list. SP_IRONWATCH_DEV_CLIENT_SECRET is
# deliberately NOT in .env; resolve it into your shell session in step 4.
# You'll also need `az login` against the ModernAnalyticsLab tenant.

# 2. Generate synthetic OREXA telemetry (reads SYNTHETIC_* vars from .env)
cd synthetic_data/generators
python generate_all.py
cd ../..

# 3. Ingest Bronze — 5x Data Pipeline Copy Activity (no notebooks; ADR-007)
python scripts/infra/build_bronze_pipelines.py

# 4. Build Silver and Gold via dbt-fabric (ADR-009/ADR-010)
set -a && source .env && set +a
export SP_IRONWATCH_DEV_CLIENT_SECRET=$(az keyvault secret show \
  --vault-name mal-kv-shared --name sp-ironwatch-dev-secret \
  --query value -o tsv)
python scripts/infra/run_dbt.py silver
python scripts/infra/run_dbt.py gold

# 5. Deploy semantic model
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
│   ├── generators/            # generate_all.py — OREXA telemetry generator
│   ├── schemas/                # JSON Schema definitions
│   └── output/                 # Generated files (gitignored)
├── notebooks/                  # Empty placeholders (.gitkeep only) — not
│                                # used; Bronze is Copy Activity, Silver/Gold
│                                # are dbt-fabric (ADR-007/ADR-009/ADR-010)
├── scripts/infra/               # Python: Fabric REST API + dbt orchestration
│                                 # (config.py, audit.py,
│                                 # build_bronze_pipelines.py, run_dbt.py) —
│                                 # no Bicep/Terraform/PowerShell
├── transform/ironwatch_gold/    # dbt project — Silver + Gold models
│                                 # (ADR-009/ADR-010)
└── semantic_model/              # Power BI TMDL / BIM files
```

## Tech Stack
| Layer | Technology |
|---|---|
| Bronze compute | Data Pipeline Copy Activity (no Spark — ADR-007) |
| Silver compute | dbt-fabric (T-SQL via Warehouse SQL endpoint) (ADR-010) |
| Gold compute | dbt-fabric (T-SQL via Warehouse SQL endpoint) (ADR-009) |
| Bronze storage | Fabric Lakehouse (Delta Lake) |
| Silver / Gold storage | Fabric Warehouse (SQL endpoint) (ADR-010, ADR-001) |
| Orchestration | Fabric Data Factory pipelines (Bronze); `scripts/infra/run_dbt.py` (Silver/Gold) |
| Audit logging | Delta table `_ironwatch_meta/execution_log`, single Bronze-hosted, cross-layer writes (ADR-010) |
| Semantic layer | Power BI semantic model (DirectLake) |
| Synthetic data | Python + Faker + NumPy |
| Infra scripting | Python (Fabric REST API + `azure-identity`) — no Bicep/Terraform/PowerShell |
| CI / PR review | CodeRabbit (`.coderabbit.yaml`) + `/ship`/`/ship-status` auto-merge workflow |

## Audit & Observability

Every pipeline run is meant to log to a single, Bronze-hosted Delta table:
`_ironwatch_meta/execution_log` (inside `ironwatch_bronze` — the only
Lakehouse of the three layers, since Warehouses can't be a direct-Delta-write
target; see [ADR-010](docs/ADR/ADR-010-silver-warehouse-dbt-scope.md)'s
"Audit table contract"). One row per run: `run_id`, `pipeline_name`, `layer`,
`status`, `rows_processed`, `error_message`, `engine`, `recorded_at`.

- **Silver/Gold:** `scripts/infra/run_dbt.py` wraps `dbt run` as a
  subprocess, parses `run_results.json`, and calls `audit.log_execution()`
  **exactly once, after** the run completes — never before, since
  `log_execution()` is append-only with no correlation mechanism (see
  ADR-010).
- **Bronze:** real audit rows exist in the table for all 5 Copy Activity
  pipelines (`engine='copy_activity'`), but `scripts/infra/build_bronze_pipelines.py`
  as currently committed does **not** call `log_execution()` anywhere — the
  actual write path for those existing rows isn't present in this repo.
  Flagged here rather than guessed at; worth investigating in a future
  session.

## CI/CD & Review Workflow

Every change lands on `develop` first; a PR to `main` goes through
CodeRabbit automated review (`.coderabbit.yaml`: `profile: chill`,
`request_changes_workflow: true`, scoped to `ironwatch-v1/**` only in this
monorepo).

- `/ship` (`.claude/commands/ship.md`): commits → pushes → opens a PR →
  polls for CodeRabbit's review → queues `gh pr merge --auto --squash` if
  the diff doesn't touch sensitive paths (Key Vault/secrets, `.coderabbit.yaml`,
  branch protection, `docs/ADR/**`, CI workflow files). Auto-merge completes
  once CodeRabbit approves; excluded-path PRs always require manual merge
  regardless of review outcome.
- `/ship-status` (`.claude/commands/ship-status.md`): checks any PRs with
  queued auto-merge and reconciles `develop`↔`main` divergence — via
  `git reset --hard origin/main`, not `rebase` (squash-merged branches
  produce false rebase conflicts even with zero real content difference).
- CodeRabbit findings aren't accepted uncritically — false positives get
  pushed back on via inline reply with technical reasoning, and CodeRabbit
  will withdraw a finding when shown to be wrong.
