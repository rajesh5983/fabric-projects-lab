# ADR-001: Gold Layer as Fabric Warehouse
Date: 2026-06-07
Status: ACCEPTED — see amendments below (2026-06-20, 2026-07-18)
Deciders: Raj Prasannakumar

> **Amendment (2026-06-20):** The compute-engine claim in the rationale
> bullet below ("Bronze and Silver remain Lakehouses written by PySpark
> notebooks") is **superseded by [ADR-007](ADR-007-spark-free-architecture.md)**:
> Bronze/Silver compute is Data Pipeline Copy Activity / Dataflow Gen2, not
> Spark. Everything else in this ADR — Gold as a Warehouse, Bronze/Silver
> as Lakehouses for *storage* — is unchanged and still in effect.

> **Amendment (2026-07-18):** The Gold transformation-language claims below
> ("Stored procedures and views are first-class" / "Gold transformation
> logic must be authored and orchestrated as T-SQL") are **superseded by
> [ADR-009](ADR-009-dbt-gold-transformation-layer.md)**: Gold transformations
> are now authored as dbt models via the `dbt-fabric` adapter, not
> hand-written stored procedures/views. Gold as a **Warehouse** (this ADR's
> storage decision) is unchanged and still in effect.

## Context
The Gold layer must do two things well: serve hourly equipment health-score
and SLA aggregations through a Power BI semantic model with sub-2-second
dashboard query response, and host the transformation logic (health-score
computation, fault rollups, oil-sample joins) that the data engineering team
will own and extend over the life of the project. Microsoft Fabric offers two
viable storage options for this layer — a **Lakehouse** (Delta tables backing
a Spark engine) and a **Warehouse** (a native SQL engine with a first-class
SQL endpoint). Bronze and Silver are already committed to Lakehouses
(Delta-backed, PySpark-authored); the open question is whether Gold should
follow that same pattern or use a different engine suited to its consumption-
facing role. This decision determines how every downstream notebook,
DirectLake connection, and v2 extension point (Fabric Data Agent MCP,
Ontology MCP) attaches to the platform.

## Decision
Provision the Gold layer as a **Fabric Warehouse** (`ironwatch_gold`), not a
Lakehouse, exposing all fact and dimension tables through its native SQL
endpoint for the semantic model and any future SQL-based consumers.

## Rationale
- **Native T-SQL surface matches team skills.** The data engineering and BI
  teams are SQL-fluent; authoring health-score logic, fault rollups, and
  incremental MERGE patterns in T-SQL (stored procedures, views) is faster
  and lower-risk than requiring PySpark expertise for the consumption layer.
- **DirectLake performance without the Spark tax.** The Warehouse SQL
  endpoint is a first-class DirectLake source for Power BI. Query plans run
  through a relational engine with statistics and distribution awareness —
  better suited to the ad-hoc star-schema joins a dashboard issues than
  Spark-SQL-over-Delta.
- **Clean separation of engineering and consumption concerns.** ~~Bronze and
  Silver remain Lakehouses written by PySpark notebooks (the right tool for
  schema validation, deduplication, and large-scale cleansing).~~ **Superseded
  by ADR-007:** Bronze and Silver remain Lakehouses for *storage*, but their
  compute is Data Pipeline Copy Activity (Bronze) and Dataflow Gen2 (Silver),
  not PySpark. Gold becomes a relational layer written in T-SQL — each layer
  uses the engine it's actually suited to, instead of forcing one engine
  across the whole pipeline.
- **Stored procedures and views are first-class.** The semantic model
  depends on recomputing health scores and SLA metrics on a schedule.
  Warehouse natively supports stored procedures, views, and full T-SQL DDL;
  Lakehouse SQL endpoints support a read-only subset that would push this
  logic back into Spark notebooks.
- **A relational SQL surface is the right shape for v2 extension points.**
  A Fabric Data Agent (MCP) or Ontology MCP server needs a stable, documented
  schema to query against. A Warehouse's SQL endpoint and information schema
  give that surface for free; a Lakehouse would require an additional
  abstraction layer to present the same contract.

## Consequences
- Gold transformation logic must be authored and orchestrated as T-SQL
  (stored procedures, views, MERGE statements) rather than Delta write
  operations — the Silver → Gold boundary becomes the pipeline's only
  cross-engine write, and every Gold notebook connects out to the Warehouse
  via its SQL endpoint instead of writing Delta files directly.
- All Gold DDL and transformation scripts must be version-controlled as
  `.sql` files (e.g., under `scripts/infra/`), since Warehouse objects are
  not notebook-native artifacts the way Delta tables are.
- The semantic model's DirectLake connection targets the Warehouse SQL
  endpoint specifically. Any future change to Gold's storage engine would
  require re-pointing and revalidating the semantic model — this decision is
  effectively load-bearing for everything downstream of Gold.

## Alternatives considered

| Alternative | Rejected because | Right when |
|---|---|---|
| Fabric Lakehouse (Delta tables) for Gold | Forces all Gold transformation logic into PySpark; Lakehouse SQL endpoints expose only a read-only subset of T-SQL, so stored-procedure-based health-score recalculation would have to live in notebooks instead | The team is Spark-fluent and Gold consumers need direct Delta/Parquet access (e.g. data-science notebooks) more than a relational SQL contract |
| Snowflake external tables over OneLake (Iceberg) | Introduces a second platform, licensing surface, and operational burden for a v1 demo scoped to a single F2 capacity; Iceberg-on-OneLake interoperability with Fabric is still maturing | Cross-platform BI or data-science tooling that specifically requires Snowflake becomes a hard requirement — already flagged as a v2 extension point in `ARCHITECTURE.md` |
| No separate Gold layer (serve BI directly from Silver) | Collapses the medallion boundary the rest of the architecture depends on; pushes health-score, SLA, and fault-aggregation logic either into Silver notebooks or the semantic model itself, both worse fits | The pipeline is small and simple enough that a direct Silver-to-BI hop carries no real modeling burden — not the case here, where health-score computation is a first-class concern |

## References
- Microsoft Fabric Warehouse documentation
- Snowflake external tables over OneLake (Iceberg)
- IronWatch ARCHITECTURE.md
