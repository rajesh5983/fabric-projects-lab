# azure-sql-hr → Fabric Mirroring: manual setup checklist

Fabric Mirroring for Azure SQL Database can't be fully scripted via CLI/Bicep —
the mirrored database item is created and configured through the Fabric portal.
This checklist covers the manual steps after `provision_sql_db.ps1` and
`load_data.ps1` have run successfully.

## 0. Prerequisites (should already be true)

- [ ] `sql-fabric-hr-demo` / `hr-erp` exists in `rg-fabric-sandbox`
      (`azure-sql-hr/provision_sql_db.ps1`), serverless Gen5, 60-min auto-pause.
- [ ] `AllowAzureServices` firewall rule (0.0.0.0–0.0.0.0) is present on the
      logical server — **required** so Fabric's mirroring engine can reach the DB.
- [ ] `sql/schema.sql` applied and `output/*.csv` loaded via
      `azure-sql-hr/load_data.ps1` (CostCenters, Employees, Timesheets, PayRuns).
- [ ] You have the `hradmin` SQL login password (or an Entra account with
      access to the database).
- [ ] You have a Fabric workspace assigned to the `fabricf2sandbox` (F2)
      capacity in `rg-fabric-sandbox`, and at least Contributor role on it.

## 1. Primary keys (already handled by schema.sql)

`sql/schema.sql` gives every table a single-column primary key so Fabric
Mirroring can replicate it:

- `CostCenters.CostCenterID`, `Timesheets.TimesheetID`, `PayRuns.PayRunID` —
  unique 1..N by construction.
- `Employees.RowID` — a generated surrogate key (1..3000). `EmpID` itself is
  **not** unique: the generator intentionally creates 90 rows with `EmpID`
  values that duplicate existing rows (messy-data "duplicate employee
  record" scenario), so it can't be a primary key directly.

No manual `ALTER TABLE` is needed — just confirm `load_data.ps1` ran against
the current `sql/schema.sql` (which includes these `PRIMARY KEY` constraints)
before configuring mirroring below.

## 2. Create the Fabric workspace / confirm capacity

- [ ] Go to https://app.fabric.microsoft.com and sign in.
- [ ] Open (or create) the workspace used for this demo.
- [ ] **Workspace settings → License info** → confirm the workspace is
      assigned to the `fabricf2sandbox` F2 capacity in `rg-fabric-sandbox`.

## 3. Create the mirrored database item

- [ ] In the workspace, select **+ New item**.
- [ ] Search for and select **Mirrored Azure SQL Database**.
- [ ] Name the item, e.g. `hr-erp-mirror`.
- [ ] On the connection screen, enter:
  - **Server**: `sql-fabric-hr-demo.database.windows.net` (confirm exact FQDN
    with `az sql server show --name sql-fabric-hr-demo --resource-group rg-fabric-sandbox --query fullyQualifiedDomainName -o tsv`)
  - **Database**: `hr-erp`
- [ ] Choose authentication:
  - **SQL Server authentication** — username `hradmin`, password set during
    `provision_sql_db.ps1`, **or**
  - **Microsoft Entra ID (organizational account)** — sign in with your Entra
    identity (must have at least `db_datareader` + permission for Fabric to
    enable change tracking, e.g. `db_owner` for a demo).
- [ ] Click **Connect** / **Next**. Fabric runs a connectivity test — if this
      fails, re-check the `AllowAzureServices` firewall rule and that the
      database isn't paused (serverless auto-resumes on connection, but the
      first connection may take ~30s).

## 4. Select tables to mirror

- [ ] On the table-selection screen, confirm `dbo.CostCenters`,
      `dbo.Employees`, `dbo.Timesheets`, and `dbo.PayRuns` all appear as
      selectable (this requires the primary keys from step 1).
- [ ] Select all four tables.
- [ ] Click **Save** / **Start mirroring**.

## 5. Verify replication

- [ ] Open the mirrored item and check the **Monitor replication** /
      Mirroring status page — initial snapshot should move from
      "Initializing" → "Running" for each table.
- [ ] Confirm row counts roughly match the source:
      CostCenters ≈ 2000, Employees ≈ 3000, Timesheets ≈ 5000, PayRuns ≈ 4000.
- [ ] Note: replication runs continuously while mirroring is on — any further
      writes to `hr-erp` (e.g. re-running `load_data.ps1`) will sync
      automatically within seconds to a couple of minutes.

## 6. Confirm zero-copy access in OneLake

- [ ] From the mirrored item, click **Open SQL analytics endpoint** (or open
      the auto-generated default semantic model / Lakehouse view) and run a
      sample query, e.g.:

```sql
SELECT TOP 10 * FROM dbo.Employees;
```

- [ ] Optionally create a **Shortcut** from a Lakehouse to the mirrored
      database's `Tables` folder in OneLake to confirm cross-item zero-copy
      access without duplicating data.

## 7. Cost / cleanup notes

- [ ] Mirroring itself doesn't add separate Azure billing — it consumes
      capacity units on `fabricf2sandbox` (F2) while the initial sync and
      ongoing change-data-capture run. Keep an eye on capacity utilization in
      the Fabric capacity metrics app if other demos are running concurrently.
- [ ] The Azure SQL DB (`sql-fabric-hr-demo`/`hr-erp`) keeps incurring storage
      cost (~AUD $5/month) even while compute auto-pauses — see
      [COST_TRACKER.md](../COST_TRACKER.md).
- [ ] To tear down after the demo: **Stop mirroring** (or delete the mirrored
      item) in Fabric first, then `az sql db delete` /
      `az sql server delete` for `hr-erp` / `sql-fabric-hr-demo`, and update
      `COST_TRACKER.md` accordingly.
