"""CLI entrypoint for API-first Microsoft Fabric bootstrap."""

from __future__ import annotations

import argparse
import json
import sys

from fabric_api_client import (
    DEFAULT_CAPACITY_NAME,
    DEFAULT_LAKEHOUSE_NAME,
    DEFAULT_LOCATION,
    DEFAULT_NOTEBOOK_NAME,
    DEFAULT_RESOURCE_GROUP,
    DEFAULT_SUBSCRIPTION_ID,
    DEFAULT_WORKSPACE_NAME,
    FabricApiClient,
    FabricApiError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the AI Agent Control Tower MVP in Microsoft Fabric using REST APIs."
    )
    parser.add_argument("--subscription-id", default=DEFAULT_SUBSCRIPTION_ID)
    parser.add_argument("--resource-group", default=DEFAULT_RESOURCE_GROUP)
    parser.add_argument("--capacity-name", default=DEFAULT_CAPACITY_NAME)
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument("--workspace-name", default=DEFAULT_WORKSPACE_NAME)
    parser.add_argument("--lakehouse-name", default=DEFAULT_LAKEHOUSE_NAME)
    parser.add_argument("--notebook-name", default=DEFAULT_NOTEBOOK_NAME)
    parser.add_argument("--resume-capacity", action="store_true")
    parser.add_argument("--suspend-after", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument(
        "--execute",
        action="store_false",
        dest="dry_run",
        help="Perform create/assign/resume/suspend calls. Plain runs remain dry-run.",
    )
    parser.add_argument("--force", action="store_true", help="Override non-F2 refusal and typed confirmations.")
    parser.add_argument("--skip-notebook", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    effective_dry_run = args.dry_run
    if effective_dry_run is None:
        effective_dry_run = not (args.resume_capacity or args.suspend_after)

    client = FabricApiClient(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        capacity_name=args.capacity_name,
        location=args.location,
        dry_run=effective_dry_run,
        force=args.force,
    )

    print("API-first Fabric bootstrap")
    print(f"Mode: {'dry-run' if effective_dry_run else 'execute'}")
    print("No Fabric resources will be deleted by this command.")

    try:
        result = client.bootstrap(
            workspace_name=args.workspace_name,
            lakehouse_name=args.lakehouse_name,
            notebook_name=args.notebook_name,
            resume_capacity=args.resume_capacity,
            suspend_after=args.suspend_after,
            skip_notebook=args.skip_notebook,
        )
    except FabricApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Stopped safely before continuing with dependent operations.", file=sys.stderr)
        return 1

    print("Bootstrap result:")
    print(
        json.dumps(
            {
                "dry_run": result.dry_run,
                "capacity_id": result.capacity_id,
                "capacity_sku": result.capacity_sku,
                "capacity_state": result.capacity_state,
                "workspace_id": result.workspace_id,
                "lakehouse_id": result.lakehouse_id,
                "notebook_id": result.notebook_id,
                "created": result.created,
                "validated": result.validated,
                "warnings": result.warnings,
            },
            indent=2,
        )
    )
    print("Final cost reminder: suspend the F SKU capacity after testing if it is no longer needed.")
    print("Fabric content on the capacity is unavailable while the capacity is paused.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
