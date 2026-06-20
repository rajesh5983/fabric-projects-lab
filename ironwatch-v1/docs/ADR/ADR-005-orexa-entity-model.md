# ADR-005: OREXA Entity Model Adopted for Synthetic Data

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
The original synthetic data generator used a generic, undocumented
CAT-style placeholder spec — `EQ-001`..`EQ-050` equipment IDs,
`789D`/`D11`/`6060 Dozer`/`16M Grader` models, `Mackay`/`Rockhampton`/
`Townsville` sites, `ENG-`/`HYD-`-prefixed fault codes. This spec existed
only in code, was never written down anywhere, and risked being mistaken
for a deliberate, documented design choice.

## Decision
Adopt the fictitious **OREXA Heavy Industries** entity model
(`docs/OREXA_SPEC.md`) as the canonical naming/entity source for all
synthetic data: Titan/Kestrel/Ironback equipment lines, three fictitious
mine sites, PulseNet/FluidLab/FleetCare subsystem naming, OX--prefixed
fault codes. This supersedes the generic placeholder spec entirely.

## Consequences
- `generate_all.py`, `docs/DATA_MODEL.md` (bumped to v1.1), and the landing
  zone blobs in `fabricf2landingsa` have all been regenerated/updated to
  match (2026-06-20).
- Generic "CAT-style" wording remaining in `README.md`, `CLAUDE.md`,
  `docs/ARCHITECTURE.md`, and `docs/WORKSPACE_DESIGN.md` is now stale
  terminology, not an active design choice — flagged in the 2026-06-20
  audit, not corrected automatically.
- Future synthetic data work (richer fault-event streams, additional
  subsystems) should extend `docs/OREXA_SPEC.md` rather than reintroducing
  ad hoc placeholder names.
