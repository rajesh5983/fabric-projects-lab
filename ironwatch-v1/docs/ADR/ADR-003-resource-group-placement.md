# ADR-003: Resource Group Placement — rg-fabric-sandbox Retained as Project Home

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
CLAUDE.md and `docs/ARCHITECTURE.md` stated that IronWatch resources must
live in `rg-ironwatch-dev` and must never use `rg-fabric-sandbox`. A
2026-06-20 environment audit found the opposite is true in practice: the F2
capacity (`fabricf2sandbox`) and the landing storage account
(`fabricf2landingsa`) already live in `rg-fabric-sandbox`, while
`rg-ironwatch-dev` is provisioned but empty and has never been used.

## Decision
Keep `rg-fabric-sandbox` as the actual resource-group home for IronWatch
infrastructure. Do not migrate the Fabric capacity or storage account to
`rg-ironwatch-dev`.

## Rationale
The capacity is already mid-build — Fabric workspaces, the planned OneLake
shortcut, and pending notebook work all anchor to it. Moving resource groups
now would mean re-provisioning or moving the capacity itself, a disruptive,
non-reversible-without-effort operation for no functional benefit this close
to active build work. Leaving documentation wrong was the actual risk, not
the resource group choice.

## Consequences
- `CLAUDE.md` updated to state `rg-fabric-sandbox` as ground truth (done
  2026-06-20).
- `rg-ironwatch-dev` remains provisioned but unused; a future cleanup pass
  should decide whether to deprovision or repurpose it.
- `docs/ARCHITECTURE.md` §5 still states the superseded "must live in
  rg-ironwatch-dev" rule and has **not** yet been updated to match this ADR
  — flagged in the 2026-06-20 audit, not corrected automatically.
