"""API-first Microsoft Fabric bootstrap client with F2 cost guardrails.

The client uses Azure CLI access tokens and Microsoft Fabric REST APIs where
available. It intentionally avoids destructive operations and defaults to
dry-run behavior through the CLI entrypoint.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


FABRIC_RESOURCE = "https://api.fabric.microsoft.com"
AZURE_RESOURCE = "https://management.azure.com"
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
AZURE_API_VERSION = "2023-11-01"

DEFAULT_SUBSCRIPTION_ID = "e82368b1-cb9b-4d92-826c-5b1e5e215d6d"
DEFAULT_RESOURCE_GROUP = "rg-fabric-sandbox"
DEFAULT_CAPACITY_NAME = "fabricf2sandbox"
DEFAULT_EXPECTED_SKU = "F2"
DEFAULT_LOCATION = "Australia East"
DEFAULT_WORKSPACE_NAME = "Agent-Control-Tower-Lab"
DEFAULT_LAKEHOUSE_NAME = "agent_control_tower_lh"
DEFAULT_NOTEBOOK_NAME = "load_agent_control_tower_data"


class FabricApiError(RuntimeError):
    """Raised when Fabric or Azure API automation cannot continue safely."""


@dataclass
class FabricBootstrapResult:
    capacity_id: str | None = None
    capacity_sku: str | None = None
    capacity_state: str | None = None
    workspace_id: str | None = None
    lakehouse_id: str | None = None
    notebook_id: str | None = None
    created: list[str] = field(default_factory=list)
    validated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = True


class FabricApiClient:
    def __init__(
        self,
        subscription_id: str = DEFAULT_SUBSCRIPTION_ID,
        resource_group: str = DEFAULT_RESOURCE_GROUP,
        capacity_name: str = DEFAULT_CAPACITY_NAME,
        expected_sku: str = DEFAULT_EXPECTED_SKU,
        location: str = DEFAULT_LOCATION,
        dry_run: bool = True,
        force: bool = False,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.capacity_name = capacity_name
        self.expected_sku = expected_sku
        self.location = location
        self.dry_run = dry_run
        self.force = force
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self._fabric_token: str | None = None
        self._azure_token: str | None = None

    @property
    def capacity_url(self) -> str:
        return (
            f"{AZURE_RESOURCE}/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.Fabric/capacities/{self.capacity_name}"
            f"?api-version={AZURE_API_VERSION}"
        )

    def get_azure_token(self, resource: str) -> str:
        command = ["az", "account", "get-access-token", "--resource", resource, "--output", "json"]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise FabricApiError("Azure CLI is not installed or not on PATH. Run az login first.") from exc
        except subprocess.CalledProcessError as exc:
            raise FabricApiError(
                "Azure CLI token acquisition failed. Run az login and confirm the active subscription. "
                f"stderr: {exc.stderr.strip()}"
            ) from exc

        token_payload = json.loads(completed.stdout)
        access_token = token_payload.get("accessToken")
        if not access_token:
            raise FabricApiError("Azure CLI did not return an access token.")
        return str(access_token)

    def fabric_headers(self) -> dict[str, str]:
        if not self._fabric_token:
            self._fabric_token = self.get_azure_token(FABRIC_RESOURCE)
        return {
            "Authorization": f"Bearer {self._fabric_token}",
            "Content-Type": "application/json",
        }

    def azure_headers(self) -> dict[str, str]:
        if not self._azure_token:
            self._azure_token = self.get_azure_token(AZURE_RESOURCE)
        return {
            "Authorization": f"Bearer {self._azure_token}",
            "Content-Type": "application/json",
        }

    def request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> requests.Response:
        retry_statuses = {429, 500, 502, 503, 504}
        last_response: requests.Response | None = None

        for attempt in range(1, 4):
            response = self.session.request(
                method,
                url,
                headers=headers,
                json=json,
                timeout=self.timeout_seconds,
            )
            last_response = response
            if response.status_code not in retry_statuses:
                break

            retry_after = response.headers.get("Retry-After")
            sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else attempt * 2
            time.sleep(sleep_seconds)

        if last_response is None:
            raise FabricApiError("No response was returned from the API request.")

        if last_response.status_code >= 400:
            raise FabricApiError(self._format_error(method, url, last_response))

        return last_response

    def _format_error(self, method: str, url: str, response: requests.Response) -> str:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text

        return (
            f"{method} {url} failed with HTTP {response.status_code}. "
            f"Response: {body}. "
            "Check permissions, tenant settings, resource names, and API support before retrying."
        )

    def get_capacity(self) -> dict[str, Any]:
        response = self.request_with_retry("GET", self.capacity_url, self.azure_headers())
        return response.json()

    def assert_capacity_is_f2(self, capacity: dict[str, Any] | None = None) -> dict[str, Any]:
        capacity = capacity or self.get_capacity()
        sku = self._capacity_sku(capacity)
        if sku != self.expected_sku and not self.force:
            raise FabricApiError(
                f"Refusing to continue because capacity SKU is '{sku}', not '{self.expected_sku}'. "
                "Use --force only if this is intentional."
            )
        return capacity

    def get_capacity_state(self, capacity: dict[str, Any] | None = None) -> str:
        capacity = capacity or self.get_capacity()
        properties = capacity.get("properties", {})
        state = properties.get("state") or properties.get("provisioningState") or "Unknown"
        return str(state)

    def resume_capacity(self, confirm: bool = True) -> dict[str, Any] | None:
        return self._capacity_action("resume", confirm=confirm)

    def suspend_capacity(self, confirm: bool = True) -> dict[str, Any] | None:
        return self._capacity_action("suspend", confirm=confirm)

    def _capacity_action(self, action: str, confirm: bool) -> dict[str, Any] | None:
        if action not in {"resume", "suspend"}:
            raise ValueError(f"Unsupported capacity action: {action}")

        action_url = self.capacity_url.replace(f"?api-version={AZURE_API_VERSION}", f"/{action}?api-version={AZURE_API_VERSION}")
        if self.dry_run:
            print(f"[dry-run] Would POST {action_url}")
            return None

        if confirm:
            expected = action.upper()
            supplied = input(f"Type {expected} to {action} Fabric capacity '{self.capacity_name}': ")
            if supplied != expected:
                raise FabricApiError(f"Capacity {action} cancelled because confirmation did not match.")

        try:
            response = self.request_with_retry("POST", action_url, self.azure_headers())
        except FabricApiError as exc:
            raise FabricApiError(
                f"Capacity {action} failed. The API version or action path may be unsupported in this tenant. {exc}"
            ) from exc

        return response.json() if response.text else {"status_code": response.status_code}

    def list_workspaces(self) -> list[dict[str, Any]]:
        response = self.request_with_retry("GET", f"{FABRIC_API_BASE}/workspaces", self.fabric_headers())
        payload = response.json()
        return list(payload.get("value", []))

    def get_workspace_by_name(self, name: str) -> dict[str, Any] | None:
        for workspace in self.list_workspaces():
            if workspace.get("displayName") == name or workspace.get("name") == name:
                return workspace
        return None

    def create_workspace(self, name: str) -> dict[str, Any]:
        if self.dry_run:
            print(f"[dry-run] Would create Fabric workspace '{name}'")
            return {"id": "dry-run-workspace-id", "displayName": name}

        response = self.request_with_retry(
            "POST",
            f"{FABRIC_API_BASE}/workspaces",
            self.fabric_headers(),
            json={"displayName": name},
        )
        return response.json()

    def assign_workspace_to_capacity(self, workspace_id: str, capacity_id: str) -> dict[str, Any] | None:
        if not capacity_id:
            raise FabricApiError(
                "Cannot assign workspace because the capacity UUID was not found in the Azure response."
            )

        url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/assignToCapacity"
        if self.dry_run:
            print(f"[dry-run] Would assign workspace '{workspace_id}' to capacity '{capacity_id}'")
            return None

        response = self.request_with_retry(
            "POST",
            url,
            self.fabric_headers(),
            json={"capacityId": capacity_id},
        )
        return response.json() if response.text else {"status_code": response.status_code}

    def list_items(self, workspace_id: str) -> list[dict[str, Any]]:
        response = self.request_with_retry(
            "GET",
            f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items",
            self.fabric_headers(),
        )
        payload = response.json()
        return list(payload.get("value", []))

    def create_lakehouse(self, workspace_id: str, display_name: str) -> dict[str, Any]:
        if self.dry_run:
            print(f"[dry-run] Would create Lakehouse '{display_name}' in workspace '{workspace_id}'")
            return {"id": "dry-run-lakehouse-id", "displayName": display_name, "type": "Lakehouse"}

        response = self.request_with_retry(
            "POST",
            f"{FABRIC_API_BASE}/workspaces/{workspace_id}/lakehouses",
            self.fabric_headers(),
            json={"displayName": display_name, "creationPayload": {"enableSchemas": True}},
        )
        return response.json() if response.text else {"status_code": response.status_code}

    def create_notebook_placeholder(self, workspace_id: str, display_name: str) -> dict[str, Any] | None:
        if self.dry_run:
            print(f"[dry-run] Would create Notebook placeholder '{display_name}' in workspace '{workspace_id}'")
            return {"id": "dry-run-notebook-id", "displayName": display_name, "type": "Notebook"}

        try:
            response = self.request_with_retry(
                "POST",
                f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items",
                self.fabric_headers(),
                json={"displayName": display_name, "type": "Notebook"},
            )
        except FabricApiError as exc:
            print(
                "Notebook placeholder creation is not supported or not permitted in this tenant. "
                "Create the notebook manually and copy notebooks/fabric_load_agent_control_tower.py into it."
            )
            print(str(exc))
            return None

        return response.json() if response.text else {"status_code": response.status_code}

    def prepare_csv_upload(self) -> list[Path]:
        data_dir = Path(__file__).resolve().parents[1] / "data"
        csv_files = sorted(data_dir.glob("*.csv"))
        if not csv_files:
            raise FabricApiError(
                "No synthetic CSV files found. Run python src/generate_synthetic_agent_runs.py first."
            )
        print("CSV files prepared for Lakehouse ingestion:")
        for csv_file in csv_files:
            print(f"- {csv_file}")
        print("Target Lakehouse Files path: Files/agent_control_tower/raw/")
        print("Use Fabric CLI upload or manual upload if direct REST file upload is unavailable.")
        return csv_files

    def bootstrap(
        self,
        workspace_name: str = DEFAULT_WORKSPACE_NAME,
        lakehouse_name: str = DEFAULT_LAKEHOUSE_NAME,
        notebook_name: str = DEFAULT_NOTEBOOK_NAME,
        resume_capacity: bool = False,
        suspend_after: bool = False,
        skip_notebook: bool = False,
    ) -> FabricBootstrapResult:
        result = FabricBootstrapResult(dry_run=self.dry_run)
        capacity = self.assert_capacity_is_f2()
        result.capacity_sku = self._capacity_sku(capacity)
        result.capacity_state = self.get_capacity_state(capacity)
        result.capacity_id = self._capacity_uuid(capacity)
        result.validated.append("capacity")

        print(f"Capacity SKU: {result.capacity_sku}")
        print(f"Capacity state: {result.capacity_state}")

        if self._is_paused(result.capacity_state):
            if not resume_capacity:
                raise FabricApiError(
                    "Fabric capacity appears to be paused. Re-run with --resume-capacity to resume explicitly."
                )
            self.resume_capacity(confirm=not self.force)
            result.created.append("capacity_resume_requested")

        workspace = self.get_workspace_by_name(workspace_name)
        if workspace:
            result.validated.append("workspace")
        else:
            workspace = self.create_workspace(workspace_name)
            result.created.append("workspace")

        workspace_id = str(workspace.get("id"))
        result.workspace_id = workspace_id
        self.assign_workspace_to_capacity(workspace_id, result.capacity_id or "")
        result.validated.append("workspace_capacity_assignment")

        items = self.list_items(workspace_id) if not self.dry_run else []
        lakehouse = self._find_item(items, lakehouse_name, "Lakehouse")
        if lakehouse:
            result.validated.append("lakehouse")
            result.lakehouse_id = str(lakehouse.get("id"))
        else:
            lakehouse = self.create_lakehouse(workspace_id, lakehouse_name)
            result.created.append("lakehouse")
            result.lakehouse_id = str(lakehouse.get("id"))

        if not skip_notebook:
            notebook = self._find_item(items, notebook_name, "Notebook")
            if notebook:
                result.validated.append("notebook")
                result.notebook_id = str(notebook.get("id"))
            else:
                notebook = self.create_notebook_placeholder(workspace_id, notebook_name)
                if notebook:
                    result.created.append("notebook")
                    result.notebook_id = str(notebook.get("id"))
                else:
                    result.warnings.append("Notebook placeholder was not created; use manual fallback.")

        self.prepare_csv_upload()

        if suspend_after:
            self.suspend_capacity(confirm=not self.force)
            result.created.append("capacity_suspend_requested")
        else:
            result.warnings.append(
                "Cost reminder: suspend the F SKU capacity after testing if it is no longer needed."
            )

        return result

    def _capacity_sku(self, capacity: dict[str, Any]) -> str:
        sku = capacity.get("sku")
        if isinstance(sku, dict):
            return str(sku.get("name") or sku.get("tier") or "Unknown")
        return str(sku or "Unknown")

    def _capacity_uuid(self, capacity: dict[str, Any]) -> str | None:
        properties = capacity.get("properties", {})
        candidates = [
            properties.get("capacityId"),
            properties.get("fabricCapacityId"),
            capacity.get("capacityId"),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return None

    def _find_item(
        self,
        items: list[dict[str, Any]],
        display_name: str,
        item_type: str,
    ) -> dict[str, Any] | None:
        for item in items:
            if item.get("displayName") == display_name and item.get("type") == item_type:
                return item
        return None

    def _is_paused(self, state: str | None) -> bool:
        if not state:
            return False
        return state.lower() in {"paused", "suspended"}
