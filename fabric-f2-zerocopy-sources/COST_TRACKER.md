# Cost Tracker — fabric-f2-zerocopy-sources

Tracks spend against **Budget-2026** ($50 AUD/month, alerts at 50%/80% to rajesh5983@gmail.com).

## Shared Resources (reused, no incremental capacity cost)

| Resource | Resource Group | Notes |
|---|---|---|
| `fabricf2sandbox` (Fabric F2 capacity) | rg-fabric-sandbox | Reused from existing sandbox. Pause via `rg-shared-infra` automation (`Pause-FabricCapacity` / `Resume-FabricCapacity`) when not actively demoing. |

## Project-Specific Resources

| Resource | Type | Resource Group | Est. Monthly Cost | Status | Notes |
|---|---|---|---|---|---|
| `sql-fabric-hr-demo` / `hr-erp` | Azure SQL DB — General Purpose, Serverless, Gen5, 1 vCore (min 0.5), 60-min auto-pause | rg-fabric-sandbox | ~AUD $5-15 (compute ~$0 while paused; ~32GB storage ~$5/mo billed even when paused) | **Provisioned** 2026-06-13, loaded with synthetic "messy ERP" HR data (CostCenters 2000, Employees 3000, Timesheets 5000, PayRuns 4000 rows) | Source DB for Fabric Mirroring zero-copy demo. Will auto-pause after 60 min idle (no actual usage cost visible yet — too recent for `az consumption` data). |

## Notes

- Pause `fabricf2sandbox` when idle to avoid F2 compute charges.
- Re-check status with:
  ```powershell
  az consumption budget show --budget-name Budget-2026 -o json
  ```
- Update this table whenever a new resource is provisioned for this project.
- **TODO (2026-06-14/15):** check `az consumption usage list` for `sql-fabric-hr-demo` /
  `hr-erp` actual cost once usage data appears (typically 24-48h after
  provisioning), and update the "Est. Monthly Cost" column with real figures.
