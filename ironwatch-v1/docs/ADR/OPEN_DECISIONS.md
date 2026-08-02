# IronWatch v1 — Open Decisions

Unresolved items that need an explicit call before downstream design can
proceed. Not numbered ADRs — listed here until resolved, then promoted to a
numbered ADR recording whichever option was chosen.

---

## OPEN-001: hours_operated / utilization tracking — RESOLVED

**Raised:** 2026-06-20, during the OREXA data-model reconciliation.
**Resolved:** 2026-06-20 — promoted to
[ADR-008](ADR-008-utilization-and-health-score-redesign.md). Option B was
rejected (would have required amending the OREXA spec); a combination of A
and C was adopted: the Silver join switches to same-calendar-day matching
instead of hours-operated proximity, and the Gold health-score formula's
service-interval term is rebuilt around calendar days since last service
instead of an hours ratio. `docs/DATA_MODEL.md` §3/§5/§7 have been rewritten
to match (v1.2, 2026-06-20).

**Problem:** The v1.0 data model design assumed an `hours_operated` field
existed on telemetry (and an `service_interval_hours` field on the asset
registry) to support two downstream pieces of logic:
- **Silver oil-sample temporal join** (`DATA_MODEL.md` §3) — matches an oil
  sample to the closest telemetry reading by `hours_operated` proximity.
- **Gold health-score formula** (`DATA_MODEL.md` §5) — penalizes assets by
  `hours_since_service ÷ service_interval_hours`.

Neither field exists in the actual generator output (it never did, even
pre-OREXA) nor in the OREXA PulseNet/asset-registry field lists. This is not
a bug to fix mechanically — it's a design gap that needs a decision on what
utilization/operating-hours tracking should actually look like.

**Options (not mutually exclusive with future iteration, but pick one to
build against first):**

| Option | Description | Trade-off |
|---|---|---|
| A. Derive from telemetry cadence | Compute utilization in the Bronze→Silver transform from cumulative telemetry timestamps/density and `engine_rpm` (e.g. running-hours estimated from non-idle reading counts) rather than carrying it as a raw field | No generator change needed; but it's an estimate, not a ground-truth hour-meter reading — temporal join precision depends on telemetry sampling rate (currently 15-min intervals) |
| B. Add `hours_operated` back as a generated field | Restore an explicit hour-meter field on PulseNet (and a `service_interval_hours`-equivalent on the asset registry), preserving the original v1.0 join/formula design without rework | Reintroduces a field not in the OREXA spec as given — would need the spec itself amended; simplest to build, least disruptive to §3/§5 designs as already written |
| C. Redesign the Gold health-score formula | Drop the operating-hours proxy entirely; recompute health score from fault frequency/severity plus elapsed calendar time since last `service_history` event (using `downtime_hours`/`service_date`, which *do* exist) instead of `hours_since_service ÷ service_interval_hours` | No new generator fields needed; but changes the formula's meaning — "time since service" instead of "usage since service" is a different (and arguably less accurate) health signal |

**Downstream impact if left unresolved:** Silver cannot be built per the
v1.0 §3 join design, and Gold cannot compute `hours_since_service` per the
v1.0 §5 formula. Both are currently flagged as known gaps in
`docs/DATA_MODEL.md` §7 rather than implemented.

**Status:** Resolved — see "Resolved" note at the top of this entry
(promoted to [ADR-008](ADR-008-utilization-and-health-score-redesign.md),
2026-06-20). This trailing line previously still read "Unresolved", left
over from before the item was actually resolved — corrected 2026-07-18.

---

## OPEN-002: No per-asset fault-event stream exists in Bronze — RESOLVED

**Raised:** 2026-08-01, during Silver build-out for `stg_fault_aggregations` /
`int_iw_fault_aggregations`.
**Resolved:** 2026-08-01 — Option A. Added `generate_fault_events()` to
`synthetic_data/generators/generate_all.py`, deriving a per-asset
fault-event stream from the existing `is_temp_anomaly`/`is_pressure_drop`/
`is_rpm_spike` telemetry anomaly signals rather than inventing occurrences
independent of telemetry. Only `OX-101`/`OX-205`/`OX-120` are ever emitted
— the 3 codes with a telemetry anomaly to derive from; the other 12
catalog codes have no signal and are never emitted. A run of ≥3
consecutive anomalous 15-min readings (45 min sustained) is required
before being promoted to a fault-event row, filtering single-reading
sensor noise. `telemetry.parquet`'s own RNG draws and output are
unchanged (masks are captured, not re-rolled) — verified byte-identical.

Landed as a 6th Bronze source: `fault_events.json` → `fault_events_raw`
via a new `pl_bronze_fault_events_load` Copy Activity pipeline, matching
the existing 5 pipelines' pattern exactly (`tableActionOption: Overwrite`,
same source-connection/sink structure — no audit-logging call, since none
of the other 5 pipelines have one either). 83 rows landed; independently
verified via direct Delta read (row count, schema, and the 3
deterministically-still-active rows all confirmed).

With SEED=42, every anomaly run happened to resolve before the 90-day
window ended, which would have left 0 active faults in the snapshot —
not useful for a "which asset needs attention now" story. Deterministically
re-opened the single most recent fault on the top 3 assets by total fault
count (ties broken by asset_id): `T320-007`, `G16-001`, `T220-011`. This
only flips an already-derived event's resolution state, not its
asset/timestamp/fault_code, and is reproducible from the fixed seed rather
than randomly forced.

`docs/DATA_MODEL.md` updated to v1.3 (§1.6 added, §1.3/§2.3/§7 updated to
match). The Silver `stg_fault_aggregations`/`int_iw_fault_aggregations`
models themselves are still not built — this resolves the Bronze-layer
field gap only; Silver build-out is a separate follow-up.

**Finding:** `fault_codes_raw` is a static 15-row code-definition catalog
only (`fault_code`/`category`/`description`/`severity`), confirmed against
all 5 Bronze sources (`telemetry_raw`, `oil_samples_raw`, `fault_codes_raw`,
`asset_master_raw`, `service_history_raw`) and the full synthetic data
generator (`synthetic_data/generators/generate_all.py`). No table or
generator function produces per-asset fault occurrences
(`asset_id`/`fault_ts`/`active_flag`/`cleared_ts`). The only anomaly concept
in the codebase is raw sensor-value drift on `telemetry_raw`
(`is_temp_anomaly`/`is_pressure_drop`/`is_rpm_spike` flags in
`generate_telemetry()`), which is not linked to `OX-` fault codes at all.

**Impact:** `int_iw_fault_aggregations` as originally scoped (join fault
events to equipment, apply an `hours_operated` not-negative check) cannot
be built — there's nothing to join or aggregate on the fault side.

**Options (not mutually exclusive with future iteration, but pick one to
build against first):**

| Option | Description | Trade-off |
|---|---|---|
| A. Extend the synthetic data generator | Add a real per-asset fault-event table (`asset_id`/`fault_ts`/`active_flag`/`cleared_ts`) to `generate_all.py` before this model can be built | Unblocks the model as originally scoped; requires a new Bronze source, a new Copy Activity pipeline, and generator/spec changes |
| B. Re-scope `stg_fault_aggregations` | Build it as a dim-style staging pass over the code catalog only (rename/cast, no aggregation); defer the per-asset fault-event stream to a later build phase | No generator change needed; ships something now, but "aggregations" in the model name no longer matches what it does, and `int_iw_fault_aggregations` stays unbuilt until Option A (or equivalent) happens later |

**Downstream impact if left unresolved:** `stg_fault_aggregations` and
`int_iw_fault_aggregations` cannot be built per the originally scoped
join/enrichment design. This was already flagged as a known gap in
`docs/DATA_MODEL.md` §7 (Still open, item 1) — this entry formalizes it as
an explicit decision point blocking the Silver fault-side build.

**Status:** Resolved — see "Resolved" note at the top of this entry.
Bronze now has a real per-asset fault-event stream; the Silver models that
consume it are a separate, still-pending follow-up.

---

## OPEN-003: OilVerdictPenalty not applied in fact_health_score — RESOLVED

**Raised:** 2026-08-02, during the Gold layer build-out (dim_asset,
dim_date, fact_telemetry, fact_health_score, fact_sla_metrics).
**Resolved:** 2026-08-02 — Option A. Added `stg_oil_samples` (1:1 staging
passthrough over `oil_samples_raw`) and
`int_iw_oil_sample_telemetry_join` (the ADR-008 §3 same-calendar-day
match to `stg_telemetry`, matching each oil sample to the telemetry
reading closest to local midday on the same calendar day; samples with
no telemetry match on that date are dropped, per Silver DQ rule 2.2.5).
`fact_health_score` now computes the full 3-term formula: OilVerdictPenalty
is the most recent matched sample's verdict per asset (Normal=0/Watch=10/
Critical=25); an asset with no matched oil sample gets penalty 0 (a
data-availability gap, not an inherent risk signal). Verified: `dbt
test` passes (including the existing health-score-range test extended to
cover the new term), and the matched-pair analysis from the original
build (isolating FaultPenalty by comparing assets with identical
days_since_service) still holds with the new term added.

**Problem:** DATA_MODEL.md §5's health-score formula (per ADR-008) has
three terms: FaultPenalty, OilVerdictPenalty, and a service-window
penalty. `fact_health_score` as built this pass only computes
FaultPenalty and the service-window penalty — OilVerdictPenalty is not
applied.

**Why:** No `stg_oil_samples` Silver model exists yet (only
`stg_equipment`, `stg_telemetry`, `stg_fault_events`, `stg_fault_codes`,
`int_iw_fault_aggregations`, and the newly-added `stg_service_history`
are built). Per ADR-008 §3, the oil-sample side additionally requires a
same-calendar-day temporal join to telemetry (matching each oil sample to
a telemetry reading on the same date) — this is materially more work
than a 1:1 staging passthrough (like `stg_service_history`) and was
scoped out of this pass as a separate, bigger build.

**Impact:** `fact_health_score.health_score` is currently a 2-of-3-term
formula (FaultPenalty + service-window penalty only). This is documented
explicitly in `fact_health_score.yml`'s model description so the model's
own docs don't silently claim the full 3-term formula. Scores are
therefore somewhat more lenient than the fully-specified formula would
produce — no asset is penalized for a poor oil-sample verdict.

**Options (not mutually exclusive with future iteration, but pick one to
build against first):**

| Option | Description | Trade-off |
|---|---|---|
| A. Build stg_oil_samples + the ADR-008 temporal join | Add the Silver staging model and the same-calendar-day match to telemetry, then wire OilVerdictPenalty into fact_health_score | Completes the documented 3-term formula; requires the temporal-join logic ADR-008 §3 describes, a non-trivial addition beyond simple staging |
| B. Leave the 2-term formula as the working definition | Treat FaultPenalty + service-window penalty as the model's real, documented scope for now; revisit if/when oil-sample data becomes a priority | No further build needed now; health scores remain less complete than DATA_MODEL.md §5's full specification until Option A happens |

**Downstream impact if left unresolved:** `fact_health_score` continues
to compute health scores without any oil-condition signal. Not a
blocker — the model is internally consistent and its docs are honest
about the gap — but it means DATA_MODEL.md §5 as written is not yet
fully implemented.

**Status:** Open — no target date set. Revisit alongside any future
Silver build-out session that adds oil-sample handling.
