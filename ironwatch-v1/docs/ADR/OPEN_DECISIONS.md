# IronWatch v1 — Open Decisions

Unresolved items that need an explicit call before downstream design can
proceed. Not numbered ADRs — listed here until resolved, then promoted to a
numbered ADR recording whichever option was chosen.

---

## OPEN-001: hours_operated / utilization tracking

**Raised:** 2026-06-20, during the OREXA data-model reconciliation.

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

**Status:** Unresolved — awaiting a decision from Rajesh.
