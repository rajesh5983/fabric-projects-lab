# ADR-001: Gold Layer Uses Fabric Warehouse (SQL Endpoint), Not Lakehouse Delta Tables

**Status:** Accepted  
**Date:** 2026-06-07  
**Deciders:** Rajesh

---

## Context
The Gold layer must serve a Power BI semantic model with sub-2-second dashboard query response times
across 50 machines × 18 months of hourly health scores (~657,000 rows/year growing).
Two storage options were evaluated: Fabric Lakehouse (Delta Lake, Parquet-backed) and Fabric Warehouse
(SQL engine, columnar storage with statistics and distribution hints).

## Decision
Use **Fabric Warehouse** for the Gold layer.

## Rationale

| Criterion | Lakehouse (Delta) | Warehouse (SQL) | Winner |
|---|---|---|---|
| SQL query performance | Good (Spark SQL) | Excellent (native SQL engine, statistics) | Warehouse |
| DirectLake support | Yes | Yes (via SQL endpoint) | Tie |
| T-SQL compatibility | Limited | Full (DDL, stored procs, views) | Warehouse |
| ACID transactions | Delta ACID | Full SQL ACID | Tie |
| Schema enforcement | Enforced | Enforced | Tie |
| BI tool integration | Via endpoint | Native SQL endpoint | Warehouse |
| Incremental load patterns | MERGE via Spark | MERGE via T-SQL | Warehouse |
| Tooling familiarity | PySpark | T-SQL | Warehouse (team SQL-fluent) |

Key deciding factor: the team is T-SQL-fluent and the semantic model team requires stored procedures
for complex health-score recalculation triggers. Fabric Warehouse natively supports both.

## Consequences
- Gold notebooks write to Warehouse via JDBC/connector, not Delta write API
- All Gold DDL lives in `scripts/infra/` as `.sql` migration scripts
- Silver → Gold boundary is the only cross-storage write; Bronze and Silver remain Delta Lakehouses
- If Fabric Warehouse query performance degrades at scale, revisit with DirectLake import mode as fallback
