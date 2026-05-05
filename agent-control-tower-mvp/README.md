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

### Microsoft Fabric Setup

1. Create a Fabric workspace for the MVP.
2. Create a Lakehouse to store synthetic telemetry, policy results, and cost tracking data.
3. Upload or generate synthetic datasets from the local project.
4. Build a Power BI semantic model over the Lakehouse tables.
5. Create dashboard pages for observability, governance outcomes, and cost optimisation.

## Disclaimer

This uses synthetic data only. Do not include secrets, production data, customer data, or live service credentials in this project.
