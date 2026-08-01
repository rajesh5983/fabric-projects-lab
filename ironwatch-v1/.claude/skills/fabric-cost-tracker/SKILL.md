---
name: fabric-cost-tracker
description: "Check actual billed Azure cost on the fabricf2sandbox Fabric capacity over a lookback window and flag likely-forgotten-Active periods (e.g. an overnight Active session). Use when asked to check Fabric capacity cost/spend, whether it was left running, or to audit recent capacity usage."
---

# /fabric-cost-tracker

Read-only cost + usage audit for `fabricf2sandbox` (resource group
`rg-fabric-sandbox`, subscription `e82368b1-cb9b-4d92-826c-5b1e5e215d6d`).
Pulls actual billed cost from Azure Cost Management, cross-references it
against capacity state-change history when that's available, and flags a
likely-forgotten Active period (e.g. paused too late, or never paused
overnight).

Never runs any write/mutating action against the subscription — cost
queries and Activity Log reads only.

## Usage

```
/fabric-cost-tracker                # default 48h lookback
/fabric-cost-tracker --hours 24     # 24h lookback
/fabric-cost-tracker --hours 72     # 72h lookback
```

## Background — read this before changing the query approach

Confirmed empirically against this subscription on 2026-08-02, before
building this skill:

- `az costmanagement query` — the `costmanagement` CLI extension as
  installable via `az extension add --name costmanagement` (v1.0.0) does
  **not** expose a `query` subcommand (only `export` and
  `show-operation-result`). Do not rely on it.
- `az consumption usage list` — runs and returns rows, but
  `pretaxCost`/`usageQuantity`/`usageStart`/`usageEnd` are all `"None"`
  for this subscription, even for a 7-14 day old window (ruling out
  billing lag as the cause). Do not rely on it for actual cost figures.
- **What works:** calling the Cost Management REST API directly via
  `az rest` (`POST .../providers/Microsoft.CostManagement/query`) returns
  real `PreTaxCost` figures. This is the only confirmed-working,
  headless, no-extension-needed path — use it.
- Cost Management's query API only supports `Daily` granularity (no
  hourly option) — there is no way to get sub-day cost resolution from
  this API. Real Active/Paused hours have to come from Activity Log
  (below), not from cost data.

**Activity Log DOES capture Fabric capacity resume/suspend actions** —
an initial version of this skill wrongly concluded otherwise. Two real
bugs caused that, both fixed in Step 3 below, not a Fabric-RP or RBAC
limitation:

1. **`--resource-id` is case-sensitive against ARM's own casing.**
   Cost Management's REST API returns `resourceId` all-lowercased
   (`.../resourcegroups/.../microsoft.fabric/capacities/...`). Passing
   that lowercased string straight into
   `az monitor activity-log list --resource-id` silently matches
   nothing. Always use the exact casing ARM itself returns (e.g. from
   `az resource show --ids ... --query id`) —
   `.../resourceGroups/.../Microsoft.Fabric/capacities/...`.
2. **`--start-time` alone does not mean "start-time through now."**
   `--offset` defaults to `6h`; when only `--start-time` is given, the
   effective query end is `start-time + 6h`, not the current time. A
   query for a broad multi-day lookback with only `--start-time` set
   silently narrows to a 6-hour slice starting at that timestamp and
   will miss events later in the intended window. Always pass an
   explicit `--end-time` alongside `--start-time`.

With both fixed, a real resume/suspend pair for this exact session
was retrieved cleanly:
`2026-08-01T00:08:31Z` (resume) → `2026-08-01T22:20:59Z` (suspend),
a confirmed 22.21-hour continuous Active window — cross-validated by
the same day's Cost Management row showing ~9.62 AUD against a
~0.00002 AUD/day idle baseline (~500,000x).

This skill's design:
- **Primary signal:** Activity Log resume/suspend pairs — exact Active
  intervals, when the query (with both fixes applied) returns data.
- **Secondary/cross-check signal:** daily `PreTaxCost` for
  fabricf2sandbox from Cost Management vs. a trailing 14-day idle
  baseline — used to flag days and corroborate Activity Log findings,
  and as the fallback if Activity Log genuinely returns nothing for a
  window (which can still happen — e.g. before this identity existed,
  or a real gap in RBAC visibility on a different account — so an
  empty result must still be reported as "inconclusive," never silently
  treated as "confirmed idle").

## Step 1 — Confirm inputs

Defaults (override only if the user names a different resource):
```
SUBSCRIPTION_ID=e82368b1-cb9b-4d92-826c-5b1e5e215d6d
RESOURCE_GROUP=rg-fabric-sandbox
CAPACITY_NAME=fabricf2sandbox
RESOURCE_ID=/subscriptions/${SUBSCRIPTION_ID}/resourcegroups/${RESOURCE_GROUP}/providers/microsoft.fabric/capacities/${CAPACITY_NAME}
HOURS=48   # from --hours, default 48
```

## Step 2 — Query actual daily cost (Cost Management REST API)

Query a window spanning `max(HOURS, 24)` hours back through now, **plus**
a 14-day trailing baseline ending where the lookback window starts (so
"normal idle cost" can be computed from real data, not guessed).

```bash
LOOKBACK_START=$(date -u -d "${HOURS} hours ago" +%Y-%m-%dT00:00:00Z)
BASELINE_START=$(date -u -d "$(date -u -d "${HOURS} hours ago" +%Y-%m-%d) -14 days" +%Y-%m-%dT00:00:00Z)
END=$(date -u +%Y-%m-%dT23:59:59Z)

BODY_FILE="$(mktemp 2>/dev/null || echo /tmp/fct_body.json)"
cat > "$BODY_FILE" <<EOF
{
  "type": "ActualCost",
  "timeframe": "Custom",
  "timePeriod": {"from": "$BASELINE_START", "to": "$END"},
  "dataset": {
    "granularity": "Daily",
    "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
    "filter": {"dimensions": {"name": "ResourceId", "operator": "In", "values": ["$RESOURCE_ID"]}},
    "grouping": [{"type": "Dimension", "name": "ResourceId"}]
  }
}
EOF

az rest --method post \
  --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body "@${BODY_FILE}" \
  -o json
```

If this errors, most likely cause is a missing `Cost Management Reader`
(or broader) role for the current identity on the subscription/resource
group — report that plainly rather than retrying blindly.

## Step 3 — Activity Log check (primary signal for hours)

Get the resource's ARM-cased ID first — do not reuse Cost Management's
lowercased `resourceId` from Step 2 (see Background, bug #1):

```bash
ARM_RESOURCE_ID=$(az resource show --ids "$RESOURCE_ID" --query id -o tsv)
```

Then query, **always passing an explicit `--end-time`** (see Background,
bug #2 — `--start-time` alone silently caps the window at `start + 6h`
via the default `--offset`):

```bash
az monitor activity-log list \
  --resource-id "$ARM_RESOURCE_ID" \
  --start-time "$LOOKBACK_START" \
  --end-time "$END" \
  -o json
```

- If this returns rows with `operationName.value` equal to
  `Microsoft.Fabric/capacities/resume/action` or
  `.../suspend/action` (filter to `status.value == 'Succeeded'` and
  `eventName.value == 'EndRequest'` to get one row per real completed
  action, not the intermediate ones), sort by `eventTimestamp` and pair
  them chronologically into Active intervals. An unmatched trailing
  `resume` (no following `suspend`) means the capacity is still Active
  as of now — treat the interval as open-ended through `$END`.
- If this returns **zero rows** after both fixes above are applied, do
  not conclude "no state changes happened" — Activity Log retention/
  RBAC can still genuinely vary by account. Print a one-line caveat and
  fall back to Step 4's cost-only flag.

## Step 4 — Classify, flag, and summarize

Compute, from Step 2's rows:
- `window_rows` = rows whose `UsageDate` falls within the lookback window
- `baseline_rows` = rows before the lookback window, within the 14-day
  baseline
- `baseline_daily_cost` = median of `baseline_rows`' `PreTaxCost` (fall
  back to min if fewer than 3 baseline rows exist)
- For each `window_rows` day: flag it if
  `PreTaxCost > max(baseline_daily_cost * 20, 0.05)` (both a relative-
  multiplier and an absolute floor, so a tiny baseline doesn't trigger a
  false flag on a trivial absolute increase — the real observed baseline
  here is ~0.00002 AUD/day against a genuine-usage day of ~9.62 AUD, a
  ~460,000x ratio, so 20x is a deliberately conservative floor, not a
  tight threshold)

If Step 3 gave real Active-interval data (the normal case once both
casing and `--end-time` are applied): sum total Active hours in the
window, total Paused hours (window duration minus Active), and flag any
single continuous Active span > 6 hours as "likely a forgotten pause."
Cross-check each Active interval's date against Step 2's flagged cost
days — they should agree; if a day is cost-flagged but has no matching
Activity Log interval (or vice versa), say so rather than silently
picking one source.

If Step 3 is genuinely empty even with both fixes applied: report the
flagged cost-days plainly, with hours marked "undeterminable headlessly —
check the Fabric Capacity Metrics app, or verify Activity Log retention/
access for this identity" rather than fabricating an hour count.

Print, in this order:
1. Total cost in the window (sum of `window_rows`' `PreTaxCost`, with
   currency).
2. Per-day breakdown (date, cost, flagged Y/N).
3. Active vs Paused hours — either the real computed figures (Step 3
   succeeded) or "undeterminable, see flagged days above" (Step 3 empty).
4. The forgotten-pause flag: clear pass/fail statement, not just raw
   numbers.

## Honesty rules

- Never report an Activity Log gap as "confirmed no activity" — always
  distinguish "no events found" from "query was mis-scoped or
  genuinely blocked." Before concluding the latter, verify: ARM-cased
  `--resource-id` (not Cost Management's lowercased one) and an
  explicit `--end-time` (not `--start-time` alone) were both used —
  these two mistakes, not RBAC, were the actual cause the one time
  this skill saw an empty result.
- Never invent an hours-Active figure when Step 3 returned no usable
  interval data — say it's undeterminable and name the real reason.
- Always show the actual baseline value used, not just the flagged
  days, so the multiplier's effect is checkable.
- This skill is read-only. It must never call `az resource
  invoke-action`, `resume`, `suspend`, or any other mutating command
  against the capacity.
