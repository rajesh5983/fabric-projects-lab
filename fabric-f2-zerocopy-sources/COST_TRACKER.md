# Cost Tracker — fabric-f2-zerocopy-sources

Tracks spend against **Budget-2026** ($50 AUD/month, alerts at 50%/80% to rajesh5983@gmail.com).

## Shared Resources (reused, no incremental capacity cost)

| Resource | Resource Group | Notes |
|---|---|---|
| `fabricf2sandbox` (Fabric F2 capacity) | rg-fabric-sandbox | Reused from existing sandbox. Pause via `rg-shared-infra` automation (`Pause-FabricCapacity` / `Resume-FabricCapacity`) when not actively demoing. |

## Project-Specific Resources

| Resource | Type | Resource Group | Est. Monthly Cost | Status | Notes |
|---|---|---|---|---|---|
| _none yet_ | | | | | |

## Notes

- Pause `fabricf2sandbox` when idle to avoid F2 compute charges.
- Re-check status with:
  ```powershell
  az consumption budget show --budget-name Budget-2026 -o json
  ```
- Update this table whenever a new resource is provisioned for this project.
