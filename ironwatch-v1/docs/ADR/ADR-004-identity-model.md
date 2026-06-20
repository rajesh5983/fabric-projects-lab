# ADR-004: Identity Model — sp-ironwatch-dev as Working Identity

**Status:** Accepted
**Date:** 2026-06-20
**Deciders:** Rajesh

---

## Context
A 2026-06-20 audit found `sp-fabric-mal` and `sp-ironwatch-dev` existed as
app registrations but held **zero role assignments anywhere** — neither
could read the landing storage account, the Fabric capacity, or even their
own secret in `mal-kv-shared`. Separately, a third, previously undocumented
identity (`mal-automation`) already held `Key Vault Secrets User` on
`mal-kv-shared` and was doing real work.

## Decision
Grant `sp-ironwatch-dev` the roles it needs to act as IronWatch's working
pipeline identity:
- `Storage Blob Data Contributor` on `fabricf2landingsa`
- `Key Vault Secrets User` on `mal-kv-shared`

Leave `mal-automation` as-is. Document it as a shared, tenant-wide
automation identity that is **not project-specific** and must not be
reassigned or removed on IronWatch's behalf.

## Consequences
- `sp-ironwatch-dev` can now read/write the landing container and read its
  own secret from the vault.
- `sp-fabric-mal` still has zero role assignments anywhere — out of scope
  for this decision; revisit if platform-level automation needs it.
- `mal-automation`'s purpose is now documented in `CLAUDE.md` so future
  audits don't mistake it for an orphaned or unauthorized identity.
