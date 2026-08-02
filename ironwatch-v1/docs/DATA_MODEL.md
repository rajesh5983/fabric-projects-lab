# IronWatch v1 — Data Model Reference

Phase 4 decisions: Bronze source inventory, Silver DQ rules, the oil-sample
temporal join, the Gold star schema, the health-score formula, SLA
metrics, and the semantic-model DAX measure stubs.

Data model version: v1.5 | Status: FINAL (Sections 1, 2, 3, 4, 5, 6)

## Changelog
- **v1.5 (2026-08-02):** First end-to-end Bronze→Silver→Gold build with
  real transformation logic — Gold's marts (`dim_asset`, `dim_date`,
  `fact_telemetry`, `fact_health_score`, `fact_sla_metrics`) are real dbt
  models now, not placeholder stubs. Adds `stg_service_history` (§2.6) to
  unlock the health-score formula's service-window term. §4 (Gold star
  schema) rewritten to match what was actually built: **grain is one row
  per asset**, not the aspirational per-asset-per-hour grain this section
  previously described — not achievable from the Silver models built so
  far (no per-hour fault/service granularity exists). `dim_fault_type`/
  `dim_oil_verdict` as separate surrogate-keyed dimensions were not built;
  fault data is consumed directly from `int_iw_fault_aggregations`
  instead. §5 (health-score formula) is now a **documented 2-of-3-term
  subset** — FaultPenalty + service-window penalty only. OilVerdictPenalty
  is not applied; see `docs/ADR/OPEN_DECISIONS.md` OPEN-003 (new, Open).
  §5 also documents a deliberate departure from ADR-008's literal
  `CURRENT_DATE` wording: `days_since_service` anchors to
  `MAX(stg_telemetry.telemetry_timestamp)` instead, since this is a frozen
  90-day synthetic dataset, not a live feed (literal `CURRENT_DATE` would
  pin every asset at the service-window penalty's max today, worsening
  further with every real day that passes despite the data never
  changing). New §6, SLA Metrics — no contract existed anywhere in this
  document before this pass (confirmed by direct search); `fact_sla_metrics`
  is a fresh, minimal, real-data-backed definition
  (`uptime_pct`/`avg_fault_resolution_hours`/`open_fault_count`). Old §6
  (DAX measure stubs) renumbered to §7; old §7 (Known Gaps) renumbered to
  §8 and updated.
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

### 2.6 `stg_service_history` — real, built dbt model (v1.5)

As of v1.5, this is a description of a real, built dbt model
(`transform/ironwatch_gold/models/staging/stg_service_history.sql`), not
a design reference like §2.1/§2.2/§2.4/§2.5. Built to unblock
`fact_health_score`'s service-window term (ADR-008) —
`days_since_service` needs a real `MAX(service_date)` per asset, which
requires this model to exist.

1:1 staging pass over `service_history_raw` (§1.5). Column rename and
type casts only — no joins, no deduplication, no `downtime_hours`
non-negative validation (the DQ-rule sketch above, items 3/4, is not
implemented against real data in this pass — the generator does not
produce duplicates or negative `downtime_hours` in practice, but the
model doesn't enforce either). Tested: `not_null` + `unique` on
`work_order_id`, `not_null` on `asset_id`/`service_date`,
`accepted_values` on `service_type`.

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

As of v1.5, this describes the schema **as actually built**, not the
v1.0-v1.4 aspirational design. The earlier diagram assumed
per-asset-per-hour grain with separate surrogate-keyed `dim_fault_type`/
`dim_oil_verdict` dimensions — not achievable from the Silver models
built so far (no per-hour fault/service granularity exists anywhere
upstream, and no `stg_oil_samples` model exists yet — see OPEN-003).

```
        dim_asset                        dim_date
  ┌─────────────────────┐         ┌─────────────────────┐
  │ asset_key (PK)      │         │ date_key (PK)       │
  │ asset_id (NK)       │         │ full_date           │
  │ equipment_line      │         │ year / month / ...  │
  │ model               │         └──────────▲──────────┘
  │ site                │                    │ date_key
  │ commission_date     │                    │
  │ status              │                    │
  │ _loaded_utc         │                    │
  └──────────▲──────────┘                    │
             │ asset_key                     │
             │                                │
  ┌──────────┴────────────────────────────────┴─────┐
  │                  fact_telemetry                  │   grain: one row per
  │ asset_key (FK) / date_key (FK) / asset_id        │   stg_telemetry reading
  │ telemetry_timestamp / sensor columns / _loaded_utc│  (15-min, unaggregated)
  └───────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │              fact_health_score                  │   grain: one row per
  │ asset_key (FK) / date_key (FK) / asset_id        │   asset (current-state
  │ active_fault_count / most_recent_fault_severity  │   snapshot, not per-hour)
  │ fault_penalty / last_service_date                │
  │ days_since_service / pct_through_service_window  │
  │ service_window_penalty / health_score            │
  │ health_band / _loaded_utc                        │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │               fact_sla_metrics                   │   grain: one row per
  │ asset_key (FK) / asset_id                        │   asset
  │ uptime_pct / avg_fault_resolution_hours          │
  │ open_fault_count / _loaded_utc                   │
  └─────────────────────────────────────────────────┘
```

| Fact | FK Column | → Dimension | Dimension Key (PK) | Notes |
|---|---|---|---|---|
| `fact_telemetry` | `asset_key` | `dim_asset` | `asset_key` | Many-to-one |
| `fact_telemetry` | `date_key` | `dim_date` | `date_key` | Many-to-one; standard YYYYMMDD date dimension |
| `fact_health_score` | `asset_key` | `dim_asset` | `asset_key` | Many-to-one; one row per asset |
| `fact_sla_metrics` | `asset_key` | `dim_asset` | `asset_key` | Many-to-one; one row per asset |

Neither `fact_health_score` nor `fact_sla_metrics` joins to `dim_date` in
a meaningful way at their current one-row-per-asset grain (there's no
per-day breakdown to key against) — both instead carry their own
snapshot-date context inline (`fact_health_score.date_key` reflects the
formula's `AS_OF_DATE`, see §5). Fault data is consumed directly from
`int_iw_fault_aggregations` (asset-grain columns: `active_fault_count`,
`most_recent_fault_severity`, etc.) rather than through a separate
surrogate-keyed `dim_fault_type` — no per-event fault dimension was
built this pass. There is no `dim_oil_verdict` either — see OPEN-003.

---

## 5. Health Score Formula

Redesigned per
[ADR-008](ADR/ADR-008-utilization-and-health-score-redesign.md) — replaces
the v1.0 service-interval term, which depended on
`hours_since_service ÷ service_interval_hours`; neither field has a source
in the OREXA Bronze inventory (§1).

**As built in `fact_health_score` (v1.5), this is a documented 2-of-3-term
subset** — OilVerdictPenalty is not applied. See
[OPEN-003](ADR/OPEN_DECISIONS.md) for why: no `stg_oil_samples` model
exists yet, and per ADR-008 §3 it needs a same-calendar-day temporal
join, a separate, bigger build than a 1:1 staging passthrough.

```
HealthScore = 100
  − (active_fault_count × FaultPenalty(most_recent_fault_severity))
  − (pct_through_service_window × 20)

FaultPenalty:                LOW = 2   MEDIUM = 5   HIGH = 10   CRITICAL = 20
pct_through_service_window:  min(days_since_service / 30.0, 1.0)
                             (1.0 -- max penalty -- if the asset has no
                             service_history row at all)
days_since_service:          AS_OF_DATE − MAX(service_history.service_date)
                             for the asset
AS_OF_DATE:                  MAX(stg_telemetry.telemetry_timestamp), NOT
                             literal CURRENT_DATE -- see note below
reference_cadence_days:      30, fixed (flat, not per-service_type --
                             ADR-008 leaves that unfixed; matches this
                             section's own worked example)

health_score is clamped to [0, 100] by construction in the model SQL.
Bands: ≥80 Healthy | 60–79 Watch | 40–59 Warning | <40 Critical
```

**FaultPenalty note:** `int_iw_fault_aggregations` exposes only the
single most-recent fault's severity, not a per-event severity breakdown
of every currently-active fault. `active_fault_count ×
FaultPenalty(most_recent_fault_severity)` is mathematically exact
whenever `active_fault_count ≤ 1` — true for every asset in the current
synthetic snapshot (OPEN-002: only 3 assets carry a single
deterministically-reopened active fault each; all others have 0).

**AS_OF_DATE note (deliberate departure from ADR-008's literal wording):**
this is a frozen 90-day synthetic dataset (telemetry ends 2026-06-06),
not a live feed. Using literal `CURRENT_DATE` for `days_since_service`
would pin every asset's service-window penalty at its −20 max as of
today's real wall-clock date, worsening further with every real day this
model is rerun, despite the underlying data never changing.
`AS_OF_DATE` instead anchors to the synthetic window's own end
(`MAX(stg_telemetry.telemetry_timestamp)`), producing real variation
across assets based on actual `service_date` differences. Confirmed as
the intended approach before building.

### Worked Example (illustrative — shows the full 3-term formula's shape;
not what `fact_health_score` currently computes, per the 2-term note above)
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

### Real Verification (2026-08-02, against the actual built model)
Matching each fault-active asset against a fault-free asset with
*identical* `days_since_service` (controlling for the independent
service-window term) isolates the FaultPenalty term exactly:

| Asset | active_fault_count | Severity | days_since_service | health_score | Matched fault-free comparison | Delta |
|---|---|---|---|---|---|---|
| `G16-001` | 1 | MEDIUM | 2 | 93.667 | `T320-009`/`K45-008`/`K45-009` (dss=2) → 98.667 | exactly −5.0 |
| `T320-007` | 1 | MEDIUM | 10 | 88.333 | `K60-001`/`K60-003` (dss=10) → 93.333 | exactly −5.0 |
| `T220-011` | 1 | LOW | 6 | 94.000 | `T220-001`/`K45-002`/`G14-001` (dss=6) → 96.000 | exactly −2.0 |

The FaultPenalty term is computed correctly, point-for-point. However,
a **raw fleet-wide ranking** of all 50 assets by `health_score` does
*not* cleanly separate all 3 fault-active assets from the pack: only
`T320-007` (88.333) is unambiguously near the bottom (2nd-worst of all
50 — only `T220-003`, fault-free but 23 days since service, scores
lower at 84.667). `G16-001` and `T220-011` land mid-pack (~32nd and
~28th of 50) because both happen to have been serviced recently, which
offsets their fault penalty. This is correct behavior for an honest
additive multi-term formula (a recently-serviced asset with a minor
fault can reasonably outscore a well-overdue fault-free one) — not a
defect — but it means the fault signal alone doesn't dominate the score
in every case, by design.

---

## 6. SLA Metrics

No contract existed anywhere in this document (or anywhere else in the
repo) prior to v1.5, confirmed by direct search — `ARCHITECTURE.md`/
`ADR-001` only used "SLA" as a generic label, never a formula or column
list. `fact_sla_metrics` is a fresh, minimal, real-data-backed
definition, one row per asset:

```
uptime_pct = 100 × (1 − SUM(stg_service_history.downtime_hours) / window_hours)
  window_hours: the full stg_telemetry min..max timestamp span — the
  same window for every asset (a uniform 90-day simulation, not
  per-asset operational calendars).

avg_fault_resolution_hours = AVG(DATEDIFF(hour, fault_ts, cleared_ts))
  over stg_fault_events rows that have actually been cleared
  (cleared_ts IS NOT NULL) for that asset. NULL for an asset with no
  cleared faults yet.

open_fault_count = int_iw_fault_aggregations.active_fault_count,
  carried through for context alongside the two metrics above.
```

These three metrics were chosen because they're directly computable
from real Silver data already built (`stg_service_history`,
`stg_fault_events`, `int_iw_fault_aggregations`) without inventing any
new upstream fields. Broader SLA concepts (e.g. contractual response-time
targets, penalty clauses) are out of scope — nothing in the OREXA spec
or Bronze inventory models a contractual SLA target to measure against.

---

## 7. Power BI Semantic Model — DAX Measure Stubs

DAX measures live in the semantic model layer (`semantic_model/`), evaluate
over the Gold Warehouse via DirectLake, and contain no calculated columns.
The following are stubs to be completed during build:

```DAX
[Health Score] =
AVERAGE ( fact_health_score[health_score] )

[Fleet at Risk] =
COUNTROWS (
    FILTER (
        VALUES ( dim_asset[asset_id] ),
        [Health Score] < 60          -- below the Watch/Warning boundary
    )
)

[Avg Days Since Service] =
AVERAGE ( fact_health_score[days_since_service] )
```

---

## 8. Known Gaps

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
  itself is unchanged and remains a catalog.

### Resolved (v1.4, via real Silver fault-side models)
- ~~`stg_fault_aggregations`/`int_iw_fault_aggregations` referenced in §2.3
  were not yet built~~ — `stg_fault_events`, `stg_fault_codes`, and
  `int_iw_fault_aggregations` are now real, tested dbt models.

### Resolved (v1.5, first end-to-end Gold build)
- ~~Gold's marts (`dim_asset`, `dim_date`, `fact_telemetry`,
  `fact_health_score`, `fact_sla_metrics`) were placeholder stubs~~ — all
  five are real dbt models now, verified via `dbt run`/`dbt test` (all
  passing) and an independent data query confirming the fault-penalty
  term computes correctly.

### Still open
- **OPEN-003** ([docs/ADR/OPEN_DECISIONS.md](ADR/OPEN_DECISIONS.md)):
  `fact_health_score`'s OilVerdictPenalty term is not applied — no
  `stg_oil_samples` model exists yet, and per ADR-008 it needs a
  same-calendar-day temporal join, a separate, bigger build than simple
  staging. The formula is a documented 2-of-3-term subset until this is
  resolved.
