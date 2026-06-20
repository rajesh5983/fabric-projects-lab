# ADR-006: Telemetry Fields Standardized to Metric Units

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
`docs/DATA_MODEL.md` (v1.0) documented telemetry fields that the generator
never actually produced — `oil_pressure_psi` in code vs. `hydraulic_
pressure_bar` in the doc. psi is also the wrong unit family for the rest of
an otherwise metric schema (bar, °C, mm/s, L/h).

## Decision
Standardize all telemetry fields to metric units; no psi anywhere in the
schema. `hydraulic_pressure_bar` (bar) replaces the old `oil_pressure_psi`
field/unit. All other fields (`coolant_temp_c`, `vibration_mms`,
`fuel_rate_lph`, `engine_rpm`, `gps_lat`/`gps_lon`) are metric or unit-less
by nature.

## Consequences
- `docs/DATA_MODEL.md` bumped to v1.1 with this reconciliation
  (2026-06-20).
- `generate_all.py` now emits `hydraulic_pressure_bar` at a heavy-equipment
  hydraulic-system pressure range (~200-280 bar nominal) — the field's
  *semantics* changed, not just its unit label; a straight psi→bar
  conversion of the old engine-oil-pressure range would have been wrong.
- Any future telemetry field additions must specify metric units up front
  in `OREXA_SPEC.md`/`DATA_MODEL.md` before being implemented in the
  generator, to prevent the doc/code drift this ADR fixes.
