# AI Agent Control Tower (Microsoft Fabric MVP)

## Overview

This project demonstrates an enterprise AI Agent Control Tower for monitoring, governance, and cost optimisation using Microsoft Fabric.

## Key Capabilities

- Observability for AI agent activity and operational telemetry
- Governance rules for policy checks and control decisions
- Cost tracking for usage analysis and optimisation
- Synthetic data simulation for local development and demos

## Architecture Summary

The MVP simulates AI agent telemetry, evaluates events through Python-based Control Tower logic, stores governed operational data in a Microsoft Fabric Lakehouse, and surfaces monitoring, governance, and cost insights through Power BI.

Core layers:

- Mock AI agents generate synthetic telemetry.
- Python logic applies policy, governance, and cost tracking rules.
- Fabric Lakehouse stores curated telemetry and policy outcomes.
- Power BI provides dashboards for operational monitoring and executive reporting.

## Setup

### Local Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Use `.env.example` as a local configuration template if environment-specific values are needed.
4. Run notebooks or Python modules against synthetic data only.

### Generate Synthetic Telemetry

Generate the local CSV datasets for the MVP with:

```bash
python src/generate_synthetic_agent_runs.py
```

The script creates synthetic-only CSV files in `data/` for agent runs, policy breaches, feedback, agent dimensions, and model dimensions. It does not connect to Fabric or any external service.

## Automated Fabric Deployment Path

Fabric CLI is the preferred deployment path for this MVP where the CLI can safely validate workspace access, validate or create Fabric items, and upload synthetic CSV files.

Install the Fabric CLI:

```bash
pip install ms-fabric-cli
```

Authenticate and confirm workspace access:

```bash
fab auth login
fab ls
```

Before running Fabric work on an F SKU capacity, run the PowerShell guardrail check with your Azure resource details:

```powershell
./scripts/fabric_capacity_guardrail.ps1 `
  -SubscriptionId "<subscription-id>" `
  -ResourceGroupName "<resource-group>" `
  -CapacityName "<capacity-name>"
```

Deploy or prepare the Lakehouse upload path with Fabric CLI:

```bash
./scripts/fabric_deploy.sh "<workspace-name>" --create-lakehouse --upload
```

Then create or open a Fabric notebook attached to the target Lakehouse and run:

```text
notebooks/fabric_load_agent_control_tower.py
```

If CLI item creation or upload is not available in your environment, manually upload the CSV files from `data/` to:

```text
Files/agent_control_tower/raw/
```

Then copy and run the notebook script in Fabric as the fallback path.

### Microsoft Fabric Setup

1. Create a Fabric workspace for the MVP.
2. Create a Lakehouse to store synthetic telemetry, policy results, and cost tracking data.
3. Upload or generate synthetic datasets from the local project.
4. Build a Power BI semantic model over the Lakehouse tables.
5. Create dashboard pages for observability, governance outcomes, and cost optimisation.

## Disclaimer

This uses synthetic data only. Do not include secrets, production data, customer data, or live service credentials in this project.
