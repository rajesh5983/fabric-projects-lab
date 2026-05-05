# Fabric F2 Cost Guardrails

Use these guardrails before running deployment, notebook, or data load steps on an F2 capacity.

## F2 Validation

- Confirm the Fabric capacity SKU is `F2` before running heavy jobs.
- Confirm the target workspace is assigned to the intended F2 capacity.
- Use `fabric_capacity_guardrail.ps1` as a pre-flight check before running Fabric work.
- Do not run large-scale tests on higher-cost capacities unless explicitly approved.

## Workload Guardrails

- Run synthetic data loads only.
- Do not connect to production systems.
- Avoid long-running Spark sessions.
- Stop or detach notebooks after validation.
- Keep test runs small and repeatable.
- Prefer CSV upload plus notebook execution for this MVP rather than complex pipelines.

## Billing Guardrails

- Pause the Fabric F SKU capacity after testing if the environment is no longer needed.
- Pausing a Fabric F SKU capacity stops active availability for content on that capacity while it is paused.
- Pausing and resuming Fabric capacity affects billing state for the capacity, but content becomes unavailable while paused.
- Resume capacity only when users need to access or run Fabric content again.
- Pause and resume actions require suitable Azure RBAC permissions on the capacity resource.

## Operational Notes

- Do not automate pause or resume actions in unattended scripts unless the operator has explicitly requested that behavior.
- Record who resumed capacity, why it was resumed, and when it should be paused again.
- Keep the MVP isolated from production data, production workspaces, and live agent services.
