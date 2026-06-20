# ADR-008: Calendar-Time-Based Join and Health Score (No hours_operated Field)

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
OPEN-001 (`docs/ADR/OPEN_DECISIONS.md`) flagged that the v1.0 design for the
Silver oil-sample temporal join (`DATA_MODEL.md` §3) and the Gold
health-score formula (`DATA_MODEL.md` §5) both depended on an
`hours_operated` field (telemetry) and a `service_interval_hours` field
(asset registry) that exist in neither the actual generator output —
before or after the OREXA pivot — nor the OREXA PulseNet/asset-registry
field lists as specified in `docs/OREXA_SPEC.md`. Three options were
weighed: (A) derive utilization from telemetry cadence, (B) reintroduce
`hours_operated`/`service_interval_hours` as generated fields, (C) redesign
the Gold formula around fault frequency and calendar time since service.

## Decision
**Reject Option B.** `docs/OREXA_SPEC.md`'s PulseNet and asset-registry
field lists were specified deliberately and exactly, twice, without these
fields — adding them back would mean overriding an explicit spec rather
than working within it.

**Adopt a combination of A and C, scoped to fields that already exist:**

1. **Silver oil-sample temporal join (§3)** is redesigned to match each oil
   sample to a telemetry reading for the same `asset_id` on the **same
   calendar day** as `sample_date`, instead of nearest `hours_operated`. An
   hours-scale tolerance (e.g. the original ±2 hours) doesn't translate
   cleanly onto `sample_date`, which is a DATE with no time-of-day
   component — same-day matching avoids assuming a sample time that isn't
   in the data. No new field is needed — `sample_date` and `timestamp`
   already exist on both sources.
2. **Gold health-score formula (§5)** replaces the
   `hours_since_service ÷ service_interval_hours` term with a term based on
   **calendar days since the asset's most recent `service_history` record**,
   weighted against a fixed reference cadence. Fault-penalty and
   oil-verdict-penalty terms are unchanged.

## Rationale
- Keeps every downstream design buildable using only fields already
  defined in `docs/OREXA_SPEC.md` — no spec amendment, no new generator
  field.
- A pure timestamp-proximity join (vs. deriving a synthetic cumulative
  "engine hours" column, as a stricter reading of Option A would require)
  is simpler to build in Dataflow Gen2 and matches what the join is
  actually for — attaching telemetry context to an oil sample at roughly
  the time it was drawn, which calendar proximity already achieves.
- A calendar-time service-interval term is a real (if different) health
  signal: "how long since this asset was last serviced" is meaningful on
  its own, even though it answers a different question than "how much has
  it been used since service."

## Consequences
- `docs/DATA_MODEL.md` §3, §5, and §7 (Known Gaps item 1 and 2) need to be
  rewritten to match this decision — **not done as part of this ADR**;
  flagged as a follow-up documentation/implementation pass.
- The exact reference cadence and weighting for the new days-since-service
  term (e.g. per `service_type`) is an implementation detail for the Gold
  build phase, not fixed by this ADR.
- `OPEN-001` in `docs/ADR/OPEN_DECISIONS.md` is resolved and promoted to
  this ADR.
