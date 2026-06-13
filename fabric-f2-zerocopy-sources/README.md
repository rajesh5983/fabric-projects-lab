# fabric-f2-zerocopy-sources

Demo project on Microsoft Fabric F2 showcasing **zero-copy data integration** —
connecting external sources into OneLake via Shortcuts, Mirroring, Eventstream,
and Fabric Link, without duplicating data into the lakehouse.

## Sources Demonstrated

| Folder | Source | Zero-Copy Pattern |
|---|---|---|
| [azure-sql-hr](./azure-sql-hr/) | Azure SQL Database (HR sample data) | Fabric Mirroring |
| [landing-zone](./landing-zone/) | ADLS Gen2 landing zone | OneLake Shortcut |
| [streaming-telemetry](./streaming-telemetry/) | Event Hub telemetry stream | Eventstream → Lakehouse/KQL DB |
| [api-weather](./api-weather/) | Public weather API | Notebook ingestion → Lakehouse |
| [dataverse-link](./dataverse-link/) | Dataverse (Dynamics 365) | Fabric Link for Dataverse |

## Environment

- Azure subscription: ModernAnalyticsLab (australiaeast)
- Fabric capacity: `fabricf2sandbox` (rg-fabric-sandbox, F2 SKU) — reused, not dedicated
- Cost guardrail: Budget-2026 ($50 AUD/month) — see [COST_TRACKER.md](./COST_TRACKER.md)

## Setup

```powershell
cd fabric-f2-zerocopy-sources
.\scripts\preflight.ps1
```

This verifies Azure CLI auth, subscription context, the `rg-fabric-sandbox` /
`fabricf2sandbox` capacity, Budget-2026 status, and creates/validates the local
Python `.venv` (faker, requests, azure-eventhub) used for synthetic data
generation and telemetry streaming.

## Project Structure

```
fabric-f2-zerocopy-sources/
├── azure-sql-hr/         # Azure SQL HR sample DB + Fabric Mirroring setup
├── landing-zone/         # ADLS landing zone + OneLake Shortcut config
├── streaming-telemetry/  # Synthetic telemetry generator + Event Hub streaming
├── api-weather/          # Weather API ingestion notebooks/scripts
├── dataverse-link/        # Dataverse → Fabric Link configuration
├── docs/                  # Architecture notes, ADRs
├── scripts/
│   └── preflight.ps1      # Environment preflight checks
├── COST_TRACKER.md         # Budget-2026 cost tracking
└── README.md
```

## Status

Scaffolded June 2026 — sources to be built out incrementally.
