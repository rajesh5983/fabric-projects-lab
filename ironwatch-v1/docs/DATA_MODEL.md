# IronWatch v1 — Data Model Reference

Phase 4 decisions: Bronze source inventory, Silver DQ rules, the oil-sample
temporal join, the Gold star schema, the health-score formula, and the
semantic-model DAX measure stubs. These decisions are final for the v1 build.

## 1. Bronze Source File Inventory (`ironwatch_bronze` Lakehouse)

Five synthetic sources are dropped as flat files (ADR-002) and landed
as schema-validated, append-only Delta tables.

### 1.1 Telemetry
- **Format:** JSON (batch drop, simulating an onboard sensor / IoT feed)
- **Simulated source:** CAT machine onboard telemetry / ECM stream

| Field | Type | Notes |
|---|---|---|
| `event_id` | STRING | UUID assigned by generator |
| `equipment_id` | STRING | e.g. `CAT-EX-014` |
| `event_ts` | TIMESTAMP | UTC, second precision |
| `engine_temp_c` | DOUBLE | °C |
| `hydraulic_pressure_bar` | DOUBLE | bar |
| `fuel_level_pct` | DOUBLE | % |
| `vibration_x` / `vibration_y` / `vibration_z` | DOUBLE | m/s² |
| `oil_pressure_bar` | DOUBLE | bar |
| `coolant_temp_c` | DOUBLE | °C |
| `load_pct` | DOUBLE | % |
| `rpm` | INT | |
| `hours_operated` | DOUBLE | Cumulative engine hours at reading time |
| `fault_code` | STRING | Nullable; populated when reading coincides with an active fault |
| `_source_file` | STRING | Simulated drop-zone path |

### 1.2 Oil Samples
- **Format:** CSV (lab batch export)
- **Simulated source:** Third-party oil-analysis lab (scheduled oil sampling / SOS report)

| Field | Type | Notes |
|---|---|---|
| `sample_id` | STRING | UUID |
| `equipment_id` | STRING | |
| `sample_date` | DATE | Date the sample was drawn |
| `hours_operated` | DOUBLE | Equipment hour-meter reading at sample time |
| `iron_ppm` | DOUBLE | Wear-metal indicator |
| `copper_ppm` | DOUBLE | Wear-metal indicator |
| `silicon_ppm` | DOUBLE | Contamination indicator |
| `viscosity_cst` | DOUBLE | Centistokes at 100°C |
| `water_pct` | DOUBLE | % water content |
| `verdict` | STRING | Lab verdict: `NORMAL` / `CAUTION` / `CRITICAL` |
| `lab_name` | STRING | Simulated lab identifier |
| `_source_file` | STRING | Simulated drop-zone path |

### 1.3 Fault Codes
- **Format:** JSON (event stream batch)
- **Simulated source:** Onboard diagnostic / ECM fault-event stream

| Field | Type | Notes |
|---|---|---|
| `fault_id` | STRING | UUID |
| `equipment_id` | STRING | |
| `fault_ts` | TIMESTAMP | UTC, when the fault was raised |
| `fault_code` | STRING | e.g. `E0420` |
| `description` | STRING | Free-text fault description |
| `severity` | STRING | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `active_flag` | BOOLEAN | `TRUE` while unresolved |
| `cleared_ts` | TIMESTAMP | Nullable; UTC when fault was cleared |
| `_source_file` | STRING | Simulated drop-zone path |

### 1.4 Asset Master
- **Format:** CSV (registry export)
- **Simulated source:** Fleet-management / ERP asset registry extract

| Field | Type | Notes |
|---|---|---|
| `equipment_id` | STRING | Natural key, e.g. `CAT-EX-014` |
| `equipment_type` | STRING | Excavator / Haul Truck / Bulldozer |
| `model` | STRING | e.g. `CAT 390F` |
| `manufacture_year` | INT | |
| `site_code` | STRING | Operating site |
| `region` | STRING | |
| `acquisition_date` | DATE | |
| `service_interval_hours` | INT | Scheduled maintenance interval |
| `status` | STRING | `ACTIVE` / `IDLE` / `RETIRED` |
| `_source_file` | STRING | Simulated drop-zone path |

### 1.5 Service History
- **Format:** CSV (work-order export)
- **Simulated source:** CMMS / maintenance work-order management system extract

| Field | Type | Notes |
|---|---|---|
| `work_order_id` | STRING | UUID |
| `equipment_id` | STRING | |
| `service_date` | DATE | |
| `service_type` | STRING | e.g. `SCHEDULED`, `UNSCHEDULED`, `INSPECTION` |
| `hours_at_service` | DOUBLE | Hour-meter reading at time of service |
| `technician_id` | STRING | |
| `parts_replaced` | STRING | Comma-separated free text |
| `notes` | STRING | Free-text technician notes |
| `_source_file` | STRING | Simulated drop-zone path |

---

## 2. Silver DQ Rules (`ironwatch_silver` Lakehouse)

Each table below lists its data-quality rules in application order, plus the
expected surviving record count as a percentage of its Bronze source volume.

### 2.1 `silver_telemetry` — expected retention: **~97% of Bronze**
1. Drop rows where `equipment_id` is null or does not match a known `dim_asset`/asset-master ID.
2. Drop rows where `event_ts` falls outside the simulation window.
3. Null out sensor values outside physically plausible ranges (e.g. `engine_temp_c` not in `-20..150`).
4. Deduplicate on `(equipment_id, event_ts)`, keeping the latest `_ingested_utc`.
5. Derive `vibration_rms = SQRT(vibration_x² + vibration_y² + vibration_z²)`.

### 2.2 `silver_oil_samples` — expected retention: **~90% of Bronze**
1. Drop records missing `equipment_id` or `sample_date`.
2. Standardize `verdict` to `{NORMAL, CAUTION, CRITICAL}` (trim, uppercase, map known synonyms).
3. Null out negative or physically impossible `ppm` / `viscosity_cst` / `water_pct` values.
4. Deduplicate on `(equipment_id, sample_date)`, keeping the most recent lab record.
5. Apply the telemetry temporal join (§3); drop the sample if no telemetry reading is found within the ±2-hour tolerance.

### 2.3 `silver_fault_codes` — expected retention: **~96% of Bronze**
1. Drop records with null `equipment_id` or `fault_code`.
2. Standardize `severity` to `{LOW, MEDIUM, HIGH, CRITICAL}`; unrecognized values default to `MEDIUM`.
3. Deduplicate on `(equipment_id, fault_code, fault_ts)`.
4. Derive `active_flag = TRUE` where `cleared_ts IS NULL`.
5. Discard records whose `fault_ts` falls outside the equipment's operational window per `asset_master`.

### 2.4 `silver_asset_master` — expected retention: **~99% of Bronze**
1. Quarantine rows with a null `equipment_id` (natural key).
2. Deduplicate on `equipment_id`, retaining the latest record as current (SCD Type 2 candidate).
3. Standardize `site_code` / `region` casing and trim whitespace.
4. Validate `service_interval_hours > 0`; null out and flag invalid values.
5. Validate `manufacture_year` falls within a plausible range (1990–current year).

### 2.5 `silver_service_history` — expected retention: **~95% of Bronze**
1. Drop records with null `equipment_id` or `service_date`.
2. Standardize `service_type` against a controlled vocabulary (`SCHEDULED` / `UNSCHEDULED` / `INSPECTION`).
3. Deduplicate on `(equipment_id, service_date, service_type)`.
4. Validate `hours_at_service` is non-negative and monotonically increasing per `equipment_id`.
5. Trim and normalize free-text `notes` and `parts_replaced` fields.

---

## 3. Silver Oil Sample Temporal Join

**In plain English:** For each oil sample record, find the telemetry reading
for the same `equipment_id` with the closest `hours_operated` value, within
±2 hours.

Oil samples are drawn at irregular calendar intervals and recorded against a
lab `sample_date`, not a precise telemetry timestamp — so they cannot be
joined to telemetry on time alone. Instead, Silver aligns each oil sample to
the equipment's *operating state* at the moment the sample was taken:

1. For a given oil sample, gather all `silver_telemetry` rows for the same
   `equipment_id`.
2. Compute `ABS(telemetry.hours_operated − oil_sample.hours_operated)` for
   each candidate row.
3. Select the candidate with the **smallest absolute difference**.
4. Accept the match only if that smallest difference is **≤ 2 hours**;
   otherwise the oil sample has no telemetry match and is dropped per DQ
   rule 2.5 (so it is never joined to a reading that doesn't represent the
   equipment's actual state when the sample was drawn).

The matched telemetry row's `event_ts` and sensor readings are then carried
onto the oil-sample record to give downstream Gold logic operating context
(e.g. engine temperature, load) at the moment the sample was taken.

---

## 4. Gold Star Schema (`ironwatch_gold` Warehouse)

```
                                  dim_date
                            ┌─────────────────────┐
                            │ date_key (PK)       │
                            │ full_date           │
                            │ year / month / ...  │
                            └──────────▲──────────┘
                                       │ date_key
        dim_asset                     │                    dim_fault_type
  ┌─────────────────────┐   ┌─────────┴──────────────┐   ┌──────────────────────┐
  │ asset_key (PK)      │   │                        │   │ fault_type_key (PK)  │
  │ equipment_id (NK)   │◀──┤  fact_equipment_health ├──▶│ fault_code (NK)      │
  │ equipment_type      │   │                        │   │ default_severity     │
  │ service_interval_   │ asset_key      fault_type_key  └──────────────────────┘
  │   hours             │   │ health_key (PK)        │
  └─────────────────────┘   │ date_key      (FK)     │
                            │ asset_key     (FK)     │
                            │ fault_type_key(FK,null)│
                            │ oil_verdict_key(FK,null)│
                            │ health_score           │
                            │ health_band            │
                            │ hours_since_service    │
                            │ _loaded_utc            │
                            └───────────┬────────────┘
                                        │ oil_verdict_key
                                        ▼
                             ┌──────────────────────┐
                             │  dim_oil_verdict     │
                             │ oil_verdict_key (PK) │
                             │ verdict (NK)         │
                             └──────────────────────┘
```

| Fact Column (FK) | → Dimension | Dimension Key (PK) | Notes |
|---|---|---|---|
| `asset_key` | `dim_asset` | `asset_key` | Many-to-one; resolves to the equipment record |
| `date_key` | `dim_date` | `date_key` | Many-to-one; standard YYYYMMDD date dimension |
| `fault_type_key` | `dim_fault_type` | `fault_type_key` | Many-to-one, **nullable** — no active fault in the period |
| `oil_verdict_key` | `dim_oil_verdict` | `oil_verdict_key` | Many-to-one, **nullable** — no recent oil sample |

`fact_equipment_health` is grained at one row per equipment per hour.

---

## 5. Health Score Formula

```
HealthScore = 100
  − Σ FaultPenalty(severity)              [summed over all currently active faults]
  − OilVerdictPenalty(verdict)            [from the most recent matched oil sample]
  − (pct_through_service_interval × 20)   [hours_since_service ÷ service_interval_hours]

FaultPenalty:        LOW = 2   MEDIUM = 5   HIGH = 10   CRITICAL = 20
OilVerdictPenalty:   NORMAL = 0   CAUTION = 10   CRITICAL = 25

Bands: ≥80 Healthy | 60–79 Watch | 40–59 Warning | <40 Critical
```

### Worked Example
Equipment with **2 active faults (1 HIGH, 1 MEDIUM)**, a **CAUTION** oil
verdict, and **80% through its service interval**:

| Term | Calculation | Value |
|---|---|---|
| Fault penalty | `HIGH (10) + MEDIUM (5)` | `−15` |
| Oil verdict penalty | `CAUTION` | `−10` |
| Service interval penalty | `0.80 × 20` | `−16` |
| **Health Score** | `100 − 15 − 10 − 16` | **`59`** |

A score of **59** falls in the **Warning** band (40–59) — just one point
below the Watch threshold, illustrating how a combination of moderate issues
(rather than any single critical one) can push equipment into the Warning
band.

---

## 6. Power BI Semantic Model — DAX Measure Stubs

DAX measures live in the semantic model layer (`semantic_model/`), evaluate
over the Gold Warehouse via DirectLake, and contain no calculated columns.
The following are stubs to be completed during build:

```DAX
[Health Score] =
AVERAGE ( fact_equipment_health[health_score] )

[Fleet at Risk] =
COUNTROWS (
    FILTER (
        VALUES ( dim_asset[equipment_id] ),
        [Health Score] < 60          -- below the Watch/Warning boundary
    )
)

[Avg Hours Since Service] =
AVERAGE ( fact_equipment_health[hours_since_service] )
```

---

Data model version: v1.0 | Status: FINAL
