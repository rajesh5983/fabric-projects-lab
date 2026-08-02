# IronWatch v1 — Data Model Reference

Phase 4 decisions: Bronze source inventory, Silver DQ rules, the oil-sample
temporal join, the Gold star schema, the health-score formula, and the
semantic-model DAX measure stubs.

Data model version: v1.4 | Status: FINAL (Sections 1, 2, 3, 4, 5)

## Changelog
- **v1.4 (2026-08-01):** Builds the Silver fault-side models that v1.3's
  Bronze-only OPEN-002 resolution deferred: `stg_fault_events` and
  `stg_fault_codes` (staging, 1:1 passthrough) and
  `int_iw_fault_aggregations` (intermediate — enrichment + per-asset
  aggregation). §2.3 rewritten to describe the models as actually built,
  replacing the earlier DQ-rule wishlist. `hours_operated` not-negative
  check re-confirmed directly against ADR-008 before building — still
  genuinely absent, not applied (see §2.3).
- **v1.3 (2026-08-01):** Resolves OPEN-002
  ([docs/ADR/OPEN_DECISIONS.md](ADR/OPEN_DECISIONS.md)). Adds a 6th Bronze
  source, `fault_events_raw` (§1.6), landed via `pl_bronze_fault_events_load`
  — a real per-asset fault-event stream
  (`asset_id`/`fault_code`/`fault_ts`/`active_flag`/`cleared_ts`) derived
  from `generate_telemetry()`'s anomaly signals, not an independent OREXA
  subsystem drop. §1.3 and §2.3 updated to point at it instead of
  `fault_codes_raw`, which remains a static code-definition catalog. §7's
  fault-event-stream gap is now resolved.
- **v1.2 (2026-06-20):** Resolves OPEN-001 per
  [ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md). §3 (oil
  sample temporal join) redesigned to same-calendar-day matching instead of
  `hours_operated` proximity. §5 (health-score formula) redesigned to a
  calendar-days-since-service term instead of
  `hours_since_service ÷ service_interval_hours`. §4 Gold star schema and §6
  DAX stub renamed `hours_since_service` → `days_since_service` to match. §7
  updated: the two gaps this resolves are marked resolved; the unrelated
  fault-event-stream gap (§2.3) remains open.
- **v1.1:** OREXA entity pivot + field/unit reconciliation.
  Bronze source inventory (§1) rewritten against `docs/OREXA_SPEC.md` and the
  actual `generate_all.py` output, replacing the generic CAT-style placeholder
  fields that this doc had described but the generator never produced (e.g.
  `hydraulic_pressure_bar`/`coolant_temp_c`/`rpm` were documented here while
  the code emitted `oil_pressure_psi`/`vibration_mms`/`fuel_rate_lph` —
  pre-existing drift, fixed as part of this pass). `equipment_id` renamed to
  `asset_id` throughout.
- **v1.0:** Initial Phase 4 decisions (Bronze inventory, Silver DQ rules,
  temporal join, Gold star schema, health-score formula, DAX stubs).

## 1. Bronze Source File Inventory (`ironwatch_bronze` Lakehouse)

Five OREXA subsystem sources (see `docs/OREXA_SPEC.md`) are dropped as flat
files (ADR-002) and landed as schema-validated, append-only Delta tables.
A 6th source, `fault_events_raw` (§1.6), was added 2026-08-01 to resolve
OPEN-002 — it is derived from PulseNet telemetry anomalies rather than an
independent OREXA subsystem file, but is dropped and landed the same way
(`fault_events.json` → `pl_bronze_fault_events_load`).

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
stream. As of v1.3, the per-asset stream exists as a separate source —
see §1.6.

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

### 1.6 Fault Events (derived from PulseNet)
- **Format:** JSON (batch drop, generated alongside the other 5 sources)
- **Simulated source:** not an independent OREXA subsystem — derived from
  `generate_telemetry()`'s `is_temp_anomaly`/`is_pressure_drop`/`is_rpm_spike`
  anomaly signals (see `synthetic_data/generators/generate_all.py`,
  `generate_fault_events()`). Resolves OPEN-002
  ([docs/ADR/OPEN_DECISIONS.md](ADR/OPEN_DECISIONS.md)).

| Field | Type | Notes |
|---|---|---|
| `asset_id` | STRING | FK to the asset registry |
| `fault_code` | STRING | FK to `fault_codes_raw`; only `OX-101`, `OX-205`, `OX-120` are ever emitted — the only 3 catalog codes with a telemetry anomaly to derive from |
| `fault_ts` | TIMESTAMP | When the underlying anomaly run started (≥3 consecutive 15-min readings sustained) |
| `active_flag` | BOOLEAN | `TRUE` while `cleared_ts` is null |
| `cleared_ts` | TIMESTAMP | Nullable; null while active. 3 of 83 rows are deterministically still active in the current snapshot (see `STILL_ACTIVE_TOP_N_ASSETS` in the generator) |

Landed via `pl_bronze_fault_events_load` — same Copy Activity pattern as
the other 5 sources, `tableActionOption: Overwrite`.

---

## 2. Silver DQ Rules (`ironwatch_silver` Warehouse)

Rules below are renamed (`equipment_id`→`asset_id`) and, as of v1.2, fully
reconciled with §1/§3/§5. As of v1.4, §2.3 describes real, built dbt
models rather than a design reference — see below for what was and
wasn't implemented against the original rule list.

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
5. Apply the telemetry temporal join (§3) — same-calendar-day matching per
   [ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md); drop the
   sample if no telemetry row exists for that asset on that date.

### 2.3 Fault-side models — `stg_fault_events`, `stg_fault_codes`, `int_iw_fault_aggregations`

As of v1.4, this is a description of real, built dbt models
(`transform/ironwatch_gold/models/staging/` and `.../intermediate/`), not
a design reference like §2.1/§2.2/§2.4/§2.5. See
`docs/ADR/OPEN_DECISIONS.md` OPEN-002 (Resolved) for the Bronze-side
history.

**`stg_fault_events`** — 1:1 staging pass over `fault_events_raw` (§1.6).
Column rename/type casts only, matching the `stg_telemetry`/`stg_equipment`
convention. Tested: `not_null` on `asset_id`/`fault_code`/`fault_ts`,
`accepted_values` on `fault_code` restricted to `{OX-101, OX-120, OX-205}`
— the only 3 codes the generator ever emits.

**`stg_fault_codes`** — 1:1 staging pass over `fault_codes_raw` (§1.3, the
static catalog). Tested: `not_null` + `unique` on `fault_code`.

**`int_iw_fault_aggregations`** — enrichment and per-asset aggregation.
Joins `stg_fault_events` to `stg_equipment` (asset attributes) and to
`stg_fault_codes` (`category`/`description`/`severity`, via a join on
`fault_code` — `severity` lives only on the catalog, not on the event
stream). Aggregates to one row per asset: `total_fault_count`,
`active_fault_count`, `distinct_fault_code_count`, and the most recent
fault's `code`/`category`/`severity`/`timestamp`. Every `stg_equipment`
asset appears exactly once, including assets with zero faults (counts
coalesced to 0). Tested: `not_null` + `relationships` back to
`stg_equipment` on `asset_id`, plus a singular test asserting
`active_fault_count` is never negative and never exceeds
`total_fault_count`.

`hours_operated` not-negative check: **not applied**, re-confirmed
directly against [ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md)
before building (Status: Accepted) — the field does not exist on any
Bronze source and Option B (reintroducing it) was explicitly rejected.
This is a confirmed absence, not an oversight.

**Deviations from the original DQ-rule sketch this section used to
describe** (kept here for traceability, not implemented in this pass):
no explicit deduplication on `(asset_id, fault_code, fault_ts)` (the
generator does not produce duplicates in practice, but the model doesn't
enforce it), and no discard of records whose `fault_ts` falls outside the
asset's operational window (no such window is currently modeled anywhere
in Bronze). Neither blocks the current build; both are candidates for a
future pass if real-world data ever needs them.

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

Redesigned per
[ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md) — replaces
the v1.0 design, which matched on `hours_operated`, a field that exists on
neither source.

**In plain English:** For each oil sample, find the telemetry reading for
the same `asset_id` recorded on the **same calendar day** as the sample.

FluidLab's `sample_date` is a DATE with no time-of-day component, while
PulseNet's `timestamp` carries full time-of-day precision — an hours-scale
tolerance window (e.g. the v1.0 design's ±2 hours) doesn't translate onto a
date-only field without an arbitrary assumption about what time of day the
sample was drawn. Matching on calendar day avoids that problem.

1. For a given oil sample, gather all `silver_telemetry` rows for the same
   `asset_id` where `DATE(timestamp) = sample_date`.
2. If at least one candidate row exists, select the reading closest to
   local midday as a representative point for that day's operating
   context.
3. If no telemetry row exists for that asset on that date, the oil sample
   has no match and is dropped per DQ rule 2.2.5.

The matched telemetry row's sensor readings (`coolant_temp_c`,
`hydraulic_pressure_bar`, etc.) are carried onto the oil-sample record to
give downstream Gold logic operating context on the day the sample was
taken.

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
                            │ days_since_service     │
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

Redesigned per
[ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md) — replaces
the v1.0 service-interval term, which depended on
`hours_since_service ÷ service_interval_hours`; neither field has a source
in the OREXA Bronze inventory (§1).

```
HealthScore = 100
  − Σ FaultPenalty(severity)              [summed over all currently active faults]
  − OilVerdictPenalty(verdict)            [from the most recent matched oil sample]
  − (pct_through_service_window × 20)     [days_since_service ÷ reference_cadence_days]

FaultPenalty:           LOW = 2   MEDIUM = 5   HIGH = 10   CRITICAL = 20
OilVerdictPenalty:       Normal = 0   Watch = 10   Critical = 25
days_since_service:      CURRENT_DATE − MAX(service_history.service_date) for the asset
reference_cadence_days:  fixed reference maintenance cadence; exact value is a
                         Gold-build-phase implementation detail, not fixed by ADR-008

Bands: ≥80 Healthy | 60–79 Watch | 40–59 Warning | <40 Critical
```

### Worked Example
Asset with **2 active faults (1 HIGH, 1 MEDIUM)**, a **Watch** oil verdict,
and **80% through its reference service window** (e.g. 24 days since
service against a 30-day reference cadence):

| Term | Calculation | Value |
|---|---|---|
| Fault penalty | `HIGH (10) + MEDIUM (5)` | `−15` |
| Oil verdict penalty | `Watch` | `−10` |
| Service window penalty | `0.80 × 20` | `−16` |
| **Health Score** | `100 − 15 − 10 − 16` | **`59`** |

A score of **59** falls in the **Warning** band (40–59) — just one point
below the Watch threshold, illustrating how a combination of moderate issues
(rather than any single critical one) can push an asset into the Warning
band. (Same numeric shape as the v1.0 example — only the service term's
units changed, from operating hours to calendar days.)

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

[Avg Days Since Service] =
AVERAGE ( fact_equipment_health[days_since_service] )
```

---

## 7. Known Gaps

### Resolved (v1.2, via [ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md))
- ~~Oil-sample temporal join (§3) and DQ rule 2.2.5 depended on
  `hours_operated`~~ — now same-calendar-day matching; no field gap.
- ~~Gold health-score formula's service-interval term (§5) depended on
  `hours_since_service ÷ service_interval_hours`~~ — now calendar
  days-since-service against a reference cadence; no field gap.

### Resolved (v1.3, via `docs/ADR/OPEN_DECISIONS.md` OPEN-002)
- ~~`fault_codes.json` is a static code-definition catalog, not a per-asset
  fault-event stream~~ — a real per-asset stream now exists as a separate
  Bronze source, `fault_events_raw` (§1.6), derived from telemetry anomaly
  signals and landed via `pl_bronze_fault_events_load`. `fault_codes_raw`
  itself is unchanged and remains a catalog. The Silver
  `stg_fault_aggregations`/`int_iw_fault_aggregations` models referenced in
  §2.3 are not yet built — this resolves the Bronze-layer field gap only.

### Still open
_None at this time._
