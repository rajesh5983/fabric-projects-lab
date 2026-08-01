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

## OPEN-002: No per-asset fault-event stream exists in Bronze

**Raised:** 2026-08-01, during Silver build-out for `stg_fault_aggregations` /
`int_iw_fault_aggregations`.

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

**Status:** OPEN — no decision made yet.
