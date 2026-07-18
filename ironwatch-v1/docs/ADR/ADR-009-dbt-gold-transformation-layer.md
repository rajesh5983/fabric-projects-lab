# ADR-009: dbt (dbt-fabric) as the Gold Transformation Layer

**Status:** Accepted
**Date:** 2026-07-18
**Deciders:** Rajesh

---

## Context
ADR-001 committed Gold's transformation logic (health-score computation,
fault rollups, oil-sample joins) to hand-written T-SQL stored procedures and
views, version-controlled as loose `.sql` files under `scripts/infra/`. As
the Gold build phase starts (ADR-008's calendar-time health-score formula
and Silver join redesign need to be implemented), that approach has no
built-in dependency graph between models, no test framework for asserting
things like "health score is between 0 and 100" or "every `asset_id` in
Gold exists in the asset registry," and no lineage/documentation generation
— all of which stored procs and views leave entirely to hand-maintained
comments. dbt is the standard tool for exactly this gap, and Microsoft
publishes `dbt-fabric`, a first-party-supported adapter that targets a
Fabric Warehouse's SQL endpoint.

## Decision
Adopt **dbt, via the `dbt-fabric` adapter, as the Gold transformation
layer**, replacing hand-written T-SQL stored procedures and views as the
mechanism that builds Gold's fact and dimension tables from Silver.

## Scope constraint
This decision is **Gold-only**. `dbt-fabric` connects to and can only write
to the **Gold Warehouse** SQL endpoint — the Bronze and Silver Lakehouse SQL
endpoints expose their Delta tables read-only, so dbt cannot target them as
a build engine even in principle. Bronze ingestion (Data Pipeline Copy
Activity) and Silver transforms (Dataflow Gen2) are unaffected by this ADR;
see **Unaffected** below.

## Supersedes
This ADR **supersedes the T-SQL stored-procedures/views language in
ADR-001's Gold section** — specifically the Rationale bullet "Stored
procedures and views are first-class" and the Consequences bullet "Gold
transformation logic must be authored and orchestrated as T-SQL (stored
procedures, views, MERGE statements)." Gold transformation logic is now
authored as dbt models (`.sql` files with Jinja + a `ref()`/`source()`
dependency graph), compiled and run against the Warehouse by `dbt-fabric`.

ADR-001's **storage** decision — Gold as a **Fabric Warehouse, not a
Lakehouse** — is unchanged and still in effect. dbt-fabric requires a
Warehouse-shaped SQL endpoint to target; this ADR is only possible because
ADR-001 already put Gold there.

## Unaffected
[ADR-007](ADR-007-spark-free-architecture.md) (Bronze via Data Pipeline Copy
Activity, Silver via Dataflow Gen2) is **unchanged** by this decision. dbt
only runs against the Gold Warehouse; it has no bearing on how Bronze or
Silver are populated, and ADR-007's Spark-free rationale for those two
layers stands as-is.

## Auth / config
`dbt-fabric`'s `profiles.yml` targets the `ironwatch_gold` Warehouse SQL
endpoint and authenticates as **`sp-ironwatch-dev`**, with the service
principal secret resolved from **`mal-kv-shared`** at runtime (e.g. via
environment variable injection sourced from Key Vault immediately before
`dbt run`, not written to disk). The secret is never hardcoded in
`profiles.yml` or committed to the repo, per the existing CLAUDE.md rule
against hardcoding credentials.

## Rationale
- **Dependency graph and incremental builds.** dbt's `ref()`/`source()`
  model graph replaces manually sequencing stored-proc calls, and supports
  incremental materializations for the health-score and fault-rollup models
  without hand-written MERGE logic.
- **Tests as a first-class concept.** dbt's built-in and custom test
  framework (not-null, accepted-range, relationships) gives Gold's
  health-score and fault-aggregation logic automated data-quality checks
  that stored procedures have no native equivalent for.
- **Lineage and documentation for free.** `dbt docs generate` produces a
  queryable lineage graph and column-level documentation from the model
  definitions themselves, which loose `.sql` files under `scripts/infra/`
  do not provide.
- **First-party Fabric support.** `dbt-fabric` is a Microsoft-published
  adapter, not a community fork — it's a supported path rather than a
  workaround.
- **Sets up CI.** A dbt project is what the forthcoming CodeRabbit /ADR
  work (separate from this one) needs to lint and review — stored procs
  scattered across `.sql` files don't give a review tool a project
  structure to reason about.

## Consequences
- Gold transformation logic moves from `scripts/infra/*.sql` (stored
  procedures, views) to a dbt project (models, tests, `profiles.yml`,
  `dbt_project.yml`) — the dbt project's location and structure are a
  separate scaffolding task, not fixed by this ADR.
- `ironwatch_gold`'s DDL is now dbt-managed; any manual T-SQL objects
  already deployed to the Warehouse from prior ADR-001-era work will need
  to be reconciled (recreated as dbt models or dropped) as part of the dbt
  scaffold — tracked separately, not done as part of this ADR.
- CI/CD for Gold becomes `dbt run` / `dbt test` invocations rather than
  deploying `.sql` scripts directly — orchestration (Fabric Data Factory
  pipeline vs. external CI runner) is an implementation detail for the dbt
  scaffold step.
- `sp-ironwatch-dev` needs (or already has, to be confirmed during
  scaffolding) write permissions on the `ironwatch_gold` Warehouse for
  `dbt run` to succeed.
- README.md's Tech Stack table is updated as part of this same change to
  reflect dbt-fabric instead of stored procs/views for Gold compute.
