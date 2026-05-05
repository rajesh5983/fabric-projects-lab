# Fabric API Automation

Module 2B provides an API-first bootstrap path for the AI Agent Control Tower MVP. It uses Azure CLI tokens, Microsoft Fabric REST APIs, and Azure management APIs for Fabric capacity checks and explicit capacity actions.

## Azure Login

Sign in with Azure CLI:

```bash
az login
az account set --subscription e82368b1-cb9b-4d92-826c-5b1e5e215d6d
```

The Python client requests tokens with:

```bash
az account get-access-token --resource https://api.fabric.microsoft.com
az account get-access-token --resource https://management.azure.com
```

## Required Permissions

Fabric API permissions and tenant settings must allow:

- `Workspace.ReadWrite.All`
- `Capacity.ReadWrite.All`
- Workspace creation permission
- Capacity contributor/admin permission

The user must also have access to the target subscription, resource group, Fabric capacity, and Fabric tenant.

## Safe Run

Run dry-run first:

```bash
python src/bootstrap_fabric_api.py --dry-run
```

Dry-run validates the intended flow and prints planned changes without creating Fabric resources, assigning capacity, resuming capacity, suspending capacity, or uploading files.

## Actual Run

To execute the bootstrap and explicitly allow capacity resume if the capacity is paused:

```bash
python src/bootstrap_fabric_api.py --resume-capacity
```

If the capacity is paused and `--resume-capacity` is not supplied, the client stops safely and tells you to rerun with the explicit flag.

## Suspend

To explicitly suspend the capacity after the run:

```bash
python src/bootstrap_fabric_api.py --suspend-after
```

Suspending an F SKU capacity helps control cost, but Fabric content assigned to the capacity becomes unavailable while paused. Pause/resume operations require Azure RBAC permissions.

## Defaults

The bootstrap defaults are:

- Subscription: `e82368b1-cb9b-4d92-826c-5b1e5e215d6d`
- Resource group: `rg-fabric-sandbox`
- Capacity: `fabricf2sandbox`
- Expected SKU: `F2`
- Location: `Australia East`
- Workspace: `Agent-Control-Tower-Lab`
- Lakehouse: `agent_control_tower_lh`
- Notebook: `load_agent_control_tower_data`

Override these values with CLI parameters when needed.

## Troubleshooting

### 401 or 403

This usually indicates an authentication, delegated scope, tenant setting, or role permission issue. Run `az login`, confirm the subscription, and verify Fabric permissions.

### 404

Confirm the subscription ID, resource group, capacity name, workspace name, and item IDs. A 404 can also occur when the signed-in identity cannot see the resource.

### API Version or Action Unsupported

Capacity resume/suspend uses Azure management endpoints. If the action path or API version is unsupported in your tenant, the client prints the failed endpoint and stops safely.

### Capacity Paused

The client refuses to continue when the capacity appears paused unless `--resume-capacity` is supplied. Resume only when you intend to make Fabric content available and restart capacity billing.

### Tenant Setting Disabled

Workspace creation, service principal access, item creation, or Fabric APIs may be blocked by tenant settings. Ask a Fabric administrator to review the relevant tenant settings.
