# IronWatch v1 — Data Model Reference

Phase 4 decisions: Bronze source inventory, Silver DQ rules, the oil-sample
temporal join, the Gold star schema, the health-score formula, and the
semantic-model DAX measure stubs.

Data model version: v1.1 | Status: FINAL (Section 1) / KNOWN GAPS (Sections 2–6, see §7)

## Changelog
- **v1.1 (2026-06-20):** OREXA entity pivot + field/unit reconciliation.
  Bronze source inventory (§1) rewritten against `docs/OREXA_SPEC.md` and the
  actual `generate_all.py` output, replacing the generic CAT-style placeholder
  fields that this doc had described but the generator never produced (e.g.
  `hydraulic_pressure_bar`/`coolant_temp_c`/`rpm` were documented here while
  the code emitted `oil_pressure_psi`/`vibration_mms`/`fuel_rate_lph` —
  pre-existing drift, fixed as part of this pass). `equipment_id` renamed to
  `asset_id` throughout. Sections 2–6 have had `equipment_id`→`asset_id`
  applied for consistency only; they still reference fields removed in the
  §1 rewrite (`hours_operated`, `service_interval_hours`, etc.) — see §7.
- **v1.0:** Initial Phase 4 decisions (Bronze inventory, Silver DQ rules,
  temporal join, Gold star schema, health-score formula, DAX stubs).

## 1. Bronze Source File Inventory (`ironwatch_bronze` Lakehouse)

Five OREXA subsystem sources (see `docs/OREXA_SPEC.md`) are dropped as flat
files (ADR-002) and landed as schema-validated, append-only Delta tables.

### 1.1 Telemetry (PulseNet)
- **Format:** Parquet (batch drop, simulating an onboard sensor / IoT feed)
- **Simulated source:** OREXA PulseNet onboard telemetry feed

| Field | Type | Notes |
|---|---|---|
| `asset_id` | STRING | e.g. `T220-001` |
| `timestamp` | TIMESTAMP | UTC |
| `engine_rpm` | INT | |
| `coolant_temp_c` | DOUBLE | °C |
| `hydraulic_pressure_bar` | DOUBLE | bar |
| `vibration_mms` | DOUBLE | mm/s |
| `fuel_rate_lph` | DOUBLE | L/h |
| `gps_lat` | DOUBLE | decimal degrees |
| `gps_lon` | DOUBLE | decimal degrees |

### 1.2 Oil Samples (FluidLab)
- **Format:** CSV (lab batch export)
- **Simulated source:** OREXA FluidLab oil-condition monitoring

| Field | Type | Notes |
|---|---|---|
| `sample_id` | STRING | UUID |
| `asset_id` | STRING | |
| `sample_date` | DATE | Date the sample was drawn |
| `iron_ppm` | DOUBLE | Wear-metal indicator |
| `viscosity_cst` | DOUBLE | Centistokes at 100°C |
| `water_content_pct` | DOUBLE | % water content |
| `particle_count` | INT | Particles per mL |
| `lab_verdict` | STRING | `Normal` / `Watch` / `Critical` |

### 1.3 Fault Codes
- **Format:** JSON (code-definition catalog)
- **Simulated source:** OREXA fault-code reference catalog (OX- prefix)

| Field | Type | Notes |
|---|---|---|
| `fault_code` | STRING | e.g. `OX-101` |
| `category` | STRING | `engine` / `hydraulic` / `electrical` / `undercarriage` / `sensor` |
| `description` | STRING | e.g. `Engine overheat` |
| `severity` | STRING | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |

This remains a **code-definition catalog**, not a per-asset fault-event
stream — see §7, item 3.

### 1.4 Asset Registry
- **Format:** CSV (registry export)
- **Simulated source:** OREXA asset registry extract

| Field | Type | Notes |
|---|---|---|
| `asset_id` | STRING | Natural key, e.g. `K60-014` |
| `equipment_line` | STRING | `Titan` / `Kestrel` / `Ironback` |
| `model` | STRING | e.g. `Titan T220` |
| `site` | STRING | `Coppervale Mine` / `Ironclad Ridge` / `Stormwood Basin` |
| `commission_date` | DATE | |
| `status` | STRING | `Active` / `Maintenance` / `Retired` |

### 1.5 Service History (FleetCare)
- **Format:** CSV (work-order export)
- **Simulated source:** OREXA FleetCare maintenance history

| Field | Type | Notes |
|---|---|---|
| `work_order_id` | STRING | UUID |
| `asset_id` | STRING | |
| `service_date` | DATE | |
| `technician_id` | STRING | |
| `service_type` | STRING | e.g. `PM_250HR`, `PM_500HR`, `PM_1000HR`, `UNPLANNED` |
| `parts_used` | STRING | Comma-separated free text |
| `downtime_hours` | DOUBLE | Hours the asset was out of service |

---

## 2. Silver DQ Rules (`ironwatch_silver` Lakehouse)

⚠️ **Not yet reconciled with §1 (see §7, item 1).** Rules below are renamed
(`equipment_id`→`asset_id`) but otherwise unchanged from v1.0; several
reference fields that no longer exist in the §1 Bronze inventory.

Each table below lists its data-quality rules in application order, plus the
expected surviving record count as a percentage of its Bronze source volume.

### 2.1 `silver_telemetry` — expected retention: **~97% of Bronze**
1. Drop rows where `asset_id` is null or does not match a known
   `dim_asset`/asset-registry ID.
2. Drop rows where `timestamp` falls outside the simulation window.
3. Null out sensor values outside physically plausible ranges (e.g.
   `coolant_temp_c` not in `-20..150`).
4. Deduplicate on `(asset_id, timestamp)`, keeping the latest `_ingested_utc`.
5. Derive `vibration_rms` from `vibration_mms` where multi-axis decomposition
   is available.

### 2.2 `silver_oil_samples` — expected retention: **~90% of Bronze**
1. Drop records missing `asset_id` or `sample_date`.
2. Standardize `lab_verdict` to `{Normal, Watch, Critical}` (trim, map known
   synonyms).
3. Null out negative or physically impossible `iron_ppm` / `viscosity_cst` /
   `water_content_pct` / `particle_count` values.
4. Deduplicate on `(asset_id, sample_date)`, keeping the most recent lab
   record.
5. ⚠️ Apply the telemetry temporal join (§3) — **this rule depends on
   `hours_operated`, which no longer exists on either source post-pivot; see
   §7, item 1.**

### 2.3 `silver_fault_codes` — expected retention: **~96% of Bronze**
⚠️ Rules 1–3 below assume per-asset fault *events*; §1.3 is a catalog with no
`asset_id`/`fault_ts`/`active_flag` columns. See §7, item 3.
1. Drop records with null `asset_id` or `fault_code`.
2. Standardize `severity` to `{LOW, MEDIUM, HIGH, CRITICAL}`; unrecognized
   values default to `MEDIUM`.
3. Deduplicate on `(asset_id, fault_code, fault_ts)`.
4. Derive `active_flag = TRUE` where `cleared_ts IS NULL`.
5. Discard records whose `fault_ts` falls outside the asset's operational
   window per the asset registry.

### 2.4 `silver_asset_registry` — expected retention: **~99% of Bronze**
1. Quarantine rows with a null `asset_id` (natural key).
2. Deduplicate on `asset_id`, retaining the latest record as current (SCD
   Type 2 candidate).
3. Standardize `site` casing and trim whitespace.
4. Validate `commission_date` falls within a plausible range.
5. Standardize `status` to `{Active, Maintenance, Retired}`.

### 2.5 `silver_service_history` — expected retention: **~95% of Bronze**
1. Drop records with null `asset_id` or `service_date`.
2. Standardize `service_type` against a controlled vocabulary (`PM_250HR` /
   `PM_500HR` / `PM_1000HR` / `UNPLANNED`).
3. Deduplicate on `(asset_id, service_date, service_type)`.
4. Validate `downtime_hours` is non-negative.
5. Trim and normalize free-text `parts_used`.

---

## 3. Silver Oil Sample Temporal Join

⚠️ **Broken by the §1 rewrite — see §7, item 1.** This join matched oil
samples to telemetry on `hours_operated`, which has been removed from both
the PulseNet and FluidLab field lists per `docs/OREXA_SPEC.md`. Left here
verbatim as the v1.0 design intent; needs a replacement join key (e.g.
nearest `timestamp`/`sample_date` instead of operating-hours proximity)
before Silver can be built.

**Original design (v1.0, now stale):** For each oil sample record, find the
telemetry reading for the same asset with the closest `hours_operated`
value, within ±2 hours, and carry its `timestamp` and sensor readings onto
the oil-sample record.

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
  │ asset_id (NK)       │◀──┤  fact_equipment_health ├──▶│ fault_code (NK)      │
  │ equipment_line      │   │                        │   │ default_severity     │
  │ model               │ asset_key      fault_type_key  └──────────────────────┘
  └─────────────────────┘   │ health_key (PK)        │
                            │ date_key      (FK)     │
                            │ asset_key     (FK)     │
                            │ fault_type_key(FK,null)│
                            │ oil_verdict_key(FK,null)│
                            │ health_score           │
                            │ health_band            │
                            │ hours_since_service    │  ⚠️ see §7, item 2
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
| `asset_key` | `dim_asset` | `asset_key` | Many-to-one; resolves to the asset record |
| `date_key` | `dim_date` | `date_key` | Many-to-one; standard YYYYMMDD date dimension |
| `fault_type_key` | `dim_fault_type` | `fault_type_key` | Many-to-one, **nullable** — no active fault in the period |
| `oil_verdict_key` | `dim_oil_verdict` | `oil_verdict_key` | Many-to-one, **nullable** — no recent oil sample |

`fact_equipment_health` is grained at one row per asset per hour.

---

## 5. Health Score Formula

⚠️ **`hours_since_service` and `service_interval_hours` no longer have a
source field — see §7, item 2.** Formula left as v1.0 design intent.

```
HealthScore = 100
  − Σ FaultPenalty(severity)              [summed over all currently active faults]
  − OilVerdictPenalty(verdict)            [from the most recent matched oil sample]
  − (pct_through_service_interval × 20)   [hours_since_service ÷ service_interval_hours]

FaultPenalty:        LOW = 2   MEDIUM = 5   HIGH = 10   CRITICAL = 20
OilVerdictPenalty:   Normal = 0   Watch = 10   Critical = 25

Bands: ≥80 Healthy | 60–79 Watch | 40–59 Warning | <40 Critical
```

### Worked Example
Asset with **2 active faults (1 HIGH, 1 MEDIUM)**, a **Watch** oil verdict,
and **80% through its service interval**:

| Term | Calculation | Value |
|---|---|---|
| Fault penalty | `HIGH (10) + MEDIUM (5)` | `−15` |
| Oil verdict penalty | `Watch` | `−10` |
| Service interval penalty | `0.80 × 20` | `−16` |
| **Health Score** | `100 − 15 − 10 − 16` | **`59`** |

A score of **59** falls in the **Warning** band (40–59) — just one point
below the Watch threshold, illustrating how a combination of moderate issues
(rather than any single critical one) can push an asset into the Warning
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
        VALUES ( dim_asset[asset_id] ),
        [Health Score] < 60          -- below the Watch/Warning boundary
    )
)

[Avg Hours Since Service] =
AVERAGE ( fact_equipment_health[hours_since_service] )
```

---

## 7. Known Gaps (introduced by the v1.1 OREXA pivot)

These are flagged, not fixed, in this pass — each requires a design decision
beyond a field rename:

1. **Oil-sample temporal join (§3) and its DQ rule (§2.2 rule 5) depend on
   `hours_operated`**, which existed in neither the old generator's actual
   output nor the new OREXA field lists for PulseNet/FluidLab. A replacement
   join strategy (e.g. nearest-timestamp) needs to be designed before Silver
   is built.
2. **`hours_since_service` (Gold fact) and `service_interval_hours` (was on
   the old asset-master table) have no source field** in the §1.4 OREXA
   asset registry or §1.5 FleetCare service history. The health-score
   formula's service-interval term (§5) needs a replacement input or a
   redesigned formula.
3. **`fault_codes.json` is a static code-definition catalog**, not a
   per-asset fault-event stream. §2.3's DQ rules and the health-score
   formula's "currently active faults" term both assume per-asset fault
   events with `asset_id`/`fault_ts`/`active_flag`/`cleared_ts`. This
   mismatch predates the OREXA pivot (the v1.0 generator never produced
   fault events either) and is unchanged by this pass.
