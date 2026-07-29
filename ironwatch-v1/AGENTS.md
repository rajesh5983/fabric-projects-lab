# AGENTS.md — IronWatch v1

Short, stable orientation for coding agents. For anything deeper, follow the
links — don't duplicate content here. See `docs/00-INDEX.md` for the full
doc map.

## What this is
Predictive equipment health platform on Microsoft Fabric, synthetic OREXA
Heavy Industries data, target: demoable Power BI semantic model by
2026-06-30. See `README.md` and `docs/ARCHITECTURE.md`.

## Tech stack
- **Bronze**: `ironwatch_bronze` Lakehouse, populated by Data Pipeline Copy
  Activity — no Spark, no notebooks ([ADR-007](docs/ADR/ADR-007-spark-free-architecture.md)).
- **Silver**: `ironwatch_silver` **Warehouse** (not a Lakehouse), built by
  `dbt-fabric` / T-SQL ([ADR-010](docs/ADR/ADR-010-silver-warehouse-dbt-scope.md)).
- **Gold**: `ironwatch_gold` **Warehouse**, built by `dbt-fabric` / T-SQL
  ([ADR-001](docs/ADR/ADR-001-gold-warehouse.md), [ADR-009](docs/ADR/ADR-009-dbt-gold-transformation-layer.md)).
- dbt project lives at `transform/ironwatch_gold/` (covers both Silver and
  Gold models, despite the folder name).
- Semantic layer: Power BI, DirectLake, DAX — see `docs/DATA_MODEL.md` §6.

## OREXA domain conventions
- Fictitious OEM. Equipment lines: **Titan** (haul trucks), **Kestrel**
  (excavators), **Ironback** (graders). Sites: Coppervale Mine, Ironclad
  Ridge, Stormwood Basin.
- `asset_id` is the join key everywhere (e.g. `T220-001`). All units metric.
- Fault codes use an `OX-` prefix, numbered by category (1xx Engine, 2xx
  Hydraulic, 3xx Electrical, 4xx Undercarriage, 5xx Sensor/telemetry).
- Full field/subsystem spec: `docs/OREXA_SPEC.md`. Schema and transform
  rules: `docs/DATA_MODEL.md`.

## Naming convention
Workspaces, Lakehouse/Warehouse names, notebook naming — defined in
`CLAUDE.md` (root) and `docs/WORKSPACE_DESIGN.md`. Do not restate or drift
from those; update the source doc instead of inventing new names here.

## Hard rules
- Never hardcode credentials or commit `.env`. Secrets resolve via
  `mal-kv-shared` Key Vault only.
- Gold is a **Warehouse**, never a Lakehouse. Silver is also a Warehouse
  (re-provisioned 2026-07-18, ADR-010) — Bronze is the only Lakehouse.
- Document architecture decisions in `docs/ADR/`, not inline in code or chat.

## Prompt 9 / IronWatchQueryAgent plan-approve gate
**Not yet defined in this repo.** No file, ADR, or backlog item currently
describes an "IronWatchQueryAgent" or a numbered-prompt plan/approve gate —
confirmed by repo-wide search 2026-07-26. Treat any reference to "Prompt 9"
as forward-looking until it's written down in `docs/03-prompts/`. Do not
infer or improvise this gate's behavior in its absence.

## Process
- Branch flow: `feature/*` → `develop` → `main`. Never commit directly to
  `main`.
- Ship via `/ship` / `/ship-status` (`.claude/commands/`) — CodeRabbit-gated
  PR to `main`. See `docs/ARCHITECTURE.md` §7.

## Off-limits for agents (don't modify without explicit instruction)
`.venv/`, `notebooks/`, `synthetic_data/`, `scripts/infra/`.

## Doc map
See `docs/00-INDEX.md`.

## Graphify
Knowledge graph rules — see CLAUDE.md.
