# ADR-010: Silver as Warehouse, dbt-fabric Spans Silver→Gold

**Status:** Proposed (draft — not yet accepted)
**Date:** 2026-07-18
**Deciders:** Rajesh

---

## Context
Silver build work was about to start, following ADR-007's Dataflow Gen2 compute decision and OPEN-001/ADR-008's already-resolved oil-sample join design. Scoping that build surfaced that ADR-007 leaves no writable T-SQL surface on `ironwatch_silver`: it is a Lakehouse, and Lakehouse SQL analytics endpoints are read-only — the identical constraint ADR-001 already documented and used as a reason to make *Gold* a Warehouse instead of a Lakehouse. `ironwatch_silver` currently holds zero tables (only Bronze ingestion has been built to date), so this is a zero-rework-cost point to reconsider the layer's storage engine before anything is built against it.

## Decision
Convert `ironwatch_silver` from a **Lakehouse** to a **Fabric Warehouse**. `dbt-fabric` (already adopted for Gold under ADR-009) is extended to own both Silver and Gold transforms as a single dbt project, targeting both Warehouses' SQL endpoints.

**Bronze is unchanged.** Still a Lakehouse, still populated via Data Pipeline Copy Activity (ADR-002/ADR-007). Stated explicitly here because this ADR touches the same document family as ADR-007 and ADR-001, and Bronze must not be assumed to move with Silver.

## Supersedes
- **ADR-001** — the "Bronze and Silver remain Lakehouses for storage" language, *Silver half only*. The Bronze half of that statement is unchanged and still in effect.
- **ADR-007** — "Silver: transforms via Dataflow Gen2." Silver compute is now dbt-fabric/T-SQL against a Warehouse, not Dataflow Gen2. ADR-007's Bronze decision (Copy Activity) is unchanged and still in effect.

## Rationale

**(a) Lakehouse SQL endpoints are read-only.** Confirmed directly in ADR-001: *"Lakehouse SQL endpoints support a read-only subset [of T-SQL] that would push this logic back into Spark notebooks."* This blocks any T-SQL or dbt write path to Silver under the prior Lakehouse design — the same constraint ADR-009 already used to scope dbt to Gold-only: *"Bronze and Silver Lakehouse SQL endpoints expose their Delta tables read-only, so dbt cannot target them as a build engine even in principle."* Converting Silver to a Warehouse removes that blocker the same way ADR-001 removed it for Gold.

**(b) The Iceberg/Snowflake interop rationale was always Gold-scoped, not Silver-scoped — confirmed, not assumed.** ADR-001's alternatives table weighs "Snowflake external tables over OneLake (Iceberg)" purely as a rejected alternative to *Gold's* storage decision. `ARCHITECTURE.md`'s v2 extension-points table states: *"**Snowflake Iceberg** | Gold tables sit on open Delta/SQL foundations, leaving a clear path to publish them as Iceberg tables..."* — Silver is not mentioned in either source. No Iceberg/Snowflake commitment exists for Silver to reverse; this decision doesn't touch that extension point at all.

**(c) Silver is currently empty.** No tables, Dataflow Gen2 queries, or pipeline assets have been built against `ironwatch_silver` — Bronze-only work has landed to date. Changing the storage engine now costs nothing beyond discarding unbuilt plans; doing it after building Dataflow Gen2 queries and a Lakehouse-shaped Silver would mean redoing that work.

## Corrections folded in
1. **`_forge_meta` does not exist anywhere in the codebase.** The real cross-layer audit table is `_ironwatch_meta/execution_log` (`scripts/infra/audit.py`). A repo-wide search confirms no prior ADR or script references `_forge_meta` — nothing to correct elsewhere — but recording this here so the name isn't introduced by confusion during the Silver build. Use `_ironwatch_meta/execution_log` in all Silver-build work and docs going forward.
2. **`AUDIT_LAYER` in `scripts/infra/audit.py` is hardcoded to `"bronze"`.** `log_execution()` always physically writes to the Bronze Lakehouse's `_ironwatch_meta/execution_log` table regardless of the `layer` argument a caller passes — that argument only lands in the record's `layer` column, not the write path. This needs to be confirmed and, if the intent is genuinely one shared audit table across all three layers, documented as such; if not, `audit.py` needs a per-layer path fix. **Not resolved by this ADR** — tracked as a prerequisite to confirm/fix before Silver build work starts logging runs.

## Open item — not resolved here
`DATA_MODEL.md` §2.3/§7: `silver_fault_codes` DQ rules 3–5 assume per-asset fault *events* (`asset_id`, `fault_ts`, `active_flag`, `cleared_ts`), but `fault_codes_raw` is a static reference/catalog table with no event columns — only `fault_code`, `category`, `description`, `severity` exist. Only rules 1–2 (null-`fault_code` drop, severity standardization) plus a `fault_code`-level dedup are buildable against the actual schema. This is a data-model gap, unrelated to and unaffected by the storage-engine decision above. Left open for resolution during the actual Silver model build, not fixed here.

## Consequences
- `ironwatch_silver` must be re-provisioned as a Fabric Warehouse (currently a Lakehouse item) before any Silver build work starts — an infrastructure change, not just a documentation change.
- Silver transformation logic is authored as dbt models (`.sql` + Jinja, `ref()`/`source()` dependency graph) inside the same dbt project ADR-009 scaffolded for Gold, rather than as Dataflow Gen2 (Power Query) queries.
- `dbt-fabric`'s `profiles.yml` gains a Silver target (or the existing target is generalized) pointing at `ironwatch_silver`'s Warehouse SQL endpoint, authenticating as `sp-ironwatch-dev` with the secret resolved from `mal-kv-shared` at runtime — the identical auth pattern ADR-009 already established for Gold.
- `docs/ARCHITECTURE.md` and `docs/WORKSPACE_DESIGN.md`'s layer tables currently describe Silver as a Lakehouse with Dataflow Gen2 compute; both need a follow-up pass to match this decision — not done as part of this ADR, per the same "flagged for follow-up, not fixed here" pattern ADR-007 used for these same two documents.
- `scripts/infra/build_bronze_pipelines.py` (Copy Activity pipeline builder) is Bronze-only and unaffected by this decision.
- Bronze is unaffected in every respect: item type, compute engine, pipelines, and audit-table location.

## Alternatives considered

| Alternative | Rejected because | Right when |
|---|---|---|
| Keep Silver as Lakehouse + Dataflow Gen2 (status quo, ADR-007) | Read-only SQL endpoint permanently blocks any future T-SQL/dbt path into Silver; forces two separate transformation paradigms (Power Query M for Silver, dbt/T-SQL for Gold) for one small solo project | Team is Power-Query-fluent and specifically wants to avoid a Warehouse-wide blast radius, or Silver genuinely never needs a SQL-based transform |
| Silver stays a Lakehouse with Dataflow Gen2; add a separate T-SQL layer only for the pieces that need it | Splits Silver transform logic across two engines with no clean boundary — more moving parts than one dbt project spanning Silver+Gold | Only a small, well-isolated subset of Silver logic needs SQL and the rest is genuinely better suited to Power Query |
| Defer this decision, keep working on Bronze-adjacent tasks | Blocks the Silver build entirely; today's task needs an unblocked path | No time pressure to start Silver yet |

## References
- ADR-001 (Gold Warehouse) — read-only Lakehouse SQL endpoint constraint; Iceberg/Snowflake alternative scoped to Gold
- ADR-007 (Spark-Free Architecture) — original Silver compute decision (Dataflow Gen2); Bronze decision (Copy Activity) unchanged by this ADR
- ADR-008 (Utilization and Health-Score Redesign) — Silver join design (same-calendar-day matching), unaffected by this storage-engine change
- ADR-009 (dbt Gold Transformation Layer) — dbt-fabric adapter, auth pattern, and Gold-only scope constraint this ADR extends to Silver
- `docs/DATA_MODEL.md` §2.3/§7 — fault_codes DQ-rule gap, left open
- `scripts/infra/audit.py` — `AUDIT_LAYER` hardcoding, flagged as a pre-build fix
- `docs/ARCHITECTURE.md` — Iceberg/Snowflake extension-point language (confirmed Gold-scoped)
