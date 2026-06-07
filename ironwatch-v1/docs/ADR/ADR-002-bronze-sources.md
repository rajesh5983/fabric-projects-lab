# ADR-002: Bronze Sources Are Flat-File Drops (ADLS Gen2) Simulated by Synthetic Generators

**Status:** Accepted  
**Date:** 2026-06-07  
**Deciders:** Rajesh

---

## Context
IronWatch v1 is a portfolio/demo project. Real CAT equipment telemetry feeds (MQTT, CAN bus, API)
are not accessible. The Bronze ingestion pattern needs to reflect a production-credible architecture
while being fully runnable offline with synthetic data.

Three source simulation options were evaluated:
1. Streaming via Azure Event Hubs / Fabric Eventstream
2. REST API simulation via a local FastAPI mock service
3. Batch flat-file drop to ADLS Gen2 (CSV/JSON)

## Decision
Use **ADLS Gen2 flat-file drops** (CSV for batch telemetry, JSON for fault event records) as the
Bronze source, simulated by Python generator scripts.

## Rationale

| Criterion | Event Hubs / Eventstream | REST API mock | ADLS flat-file drop | Winner |
|---|---|---|---|---|
| Infrastructure cost | High (Event Hubs namespace) | Low (local) | Low (ADLS LRS) | Tie: API / ADLS |
| Realism for demo | High (streaming) | Medium | High (batch ingest pattern common in industry) | Tie |
| Offline runnable | No | Yes | Yes (Azurite emulator) | ADLS / API |
| Complexity to scaffold | High | Medium | Low | ADLS |
| Production upgrade path | Direct | Requires rework | Easy: swap generator for real MQTT bridge | ADLS |
| Fabric native support | Eventstream connector | Custom | Data Factory file trigger | ADLS |

Flat-file drop wins on simplicity, cost, and upgrade path. ADLS Gen2 is the most common real-world
Bronze source pattern for equipment OEM batch telemetry exports (daily/hourly file drops from edge gateways).

## Consequences
- `synthetic_data/generators/` scripts produce files in `synthetic_data/output/` matching ADLS structure
- Files are uploaded to the `ironwatch-raw` ADLS container by a setup script in `scripts/infra/`
- Bronze ingestion triggered by Fabric Data Factory `pl_bronze_telemetry_load` on file arrival
- When real telemetry is available, replace generator + upload step with MQTT-to-ADLS bridge; pipeline unchanged
- Local testing uses Azurite (Azure Storage emulator); configure via `ADLS_ACCOUNT_NAME=devstoreaccount1`
