# IronWatch v1 — Solution Architecture

## Overview
IronWatch v1 monitors and predicts the health of heavy equipment (CAT-style: excavators, haul trucks,
bulldozers) by processing high-frequency sensor telemetry through a Microsoft Fabric medallion pipeline.

## Data Flow

```
┌─────────────────────┐
│  Synthetic Generator │  Python scripts produce JSON/CSV telemetry events
│  (or real MQTT feed) │  simulating 50 machines × 90 days × 12 metrics
└─────────┬───────────┘
          │ ADLS Gen2 drop (ironwatch-raw container)
          ▼
┌─────────────────────┐
│   Bronze Lakehouse   │  Schema-validated, append-only Delta tables
│  ironwatch-bronze    │  Partitioned by event_date
│                      │  Retained: raw_telemetry, raw_fault_code
└─────────┬───────────┘
          │ Fabric Notebook (PySpark)
          ▼
┌─────────────────────┐
│   Silver Lakehouse   │  Deduplicated, typed, null-handled
│  ironwatch-silver    │  machine_telemetry (1-min averages)
│                      │  machine_fault (enriched fault events)
└─────────┬───────────┘
          │ Fabric Notebook (PySpark)
          ▼
┌─────────────────────┐
│   Gold Warehouse     │  T-SQL aggregations, health score computation
│  ironwatch-gold      │  fact_equipment_health (hourly)
│                      │  dim_machine, dim_date, dim_fault_type
└─────────┬───────────┘
          │ DirectLake connection
          ▼
┌─────────────────────┐
│  Power BI Semantic   │  DAX measures: HealthScore, MTBF, SLACompliance
│       Model          │  RLS by region/site
│  ironwatch-semantic  │  Composite model (DirectLake + import for slow dims)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Operations Dashboard│  Equipment health tiles, alert inbox, trend charts
└─────────────────────┘
```

## Key Components

### Synthetic Telemetry Generator
- 12 sensor channels per machine: engine_temp, hydraulic_pressure, fuel_level,
  vibration_x/y/z, oil_pressure, coolant_temp, load_percent, rpm, hours_operated, fault_code
- Fault injection: random Gaussian anomalies seeded by machine age and operating environment
- Output formats: JSON (streaming simulation), CSV (batch drop)

### Health Score Algorithm (Gold layer)
```
HealthScore = 100
  - (engine_temp_deviation × 0.25)
  - (vibration_severity × 0.30)
  - (fault_frequency_7d × 0.20)
  - (hours_since_service / service_interval × 0.25)
```
Score range: 0–100. Thresholds: ≥80 Healthy, 60–79 Watch, 40–59 Warning, <40 Critical.

### Orchestration
Fabric Data Factory pipeline `pl_bronze_telemetry_load` triggers on new file arrival in ADLS.
Silver and Gold notebooks are chained via pipeline activities with dependency gates.

## Non-Functional Requirements
| Concern | Target |
|---|---|
| Batch latency | < 15 min end-to-end (generator → Gold) |
| Gold query SLA | < 2 s for dashboard queries |
| Data retention | Bronze: 2 years, Silver: 5 years, Gold: indefinite |
| Cost cap (dev) | F2 SKU, auto-pause after 2 h idle |
