# Architecture

## High-Level Architecture

The AI Agent Control Tower MVP uses synthetic agent telemetry to demonstrate how Microsoft Fabric can support enterprise monitoring, governance, and cost optimisation for AI agent workloads.

The architecture separates telemetry generation, policy evaluation, storage, and reporting so each layer can evolve independently as the MVP matures.

## Components

### AI Agents (mock)

Mock AI agents simulate user requests, agent actions, tool usage, outcomes, latency, token usage, and estimated cost. These agents do not connect to external services.

### Control Tower Logic (Python)

Python logic processes synthetic telemetry, applies governance rules, calculates usage and cost metrics, and prepares curated datasets for analytics.

### Fabric Lakehouse

The Fabric Lakehouse stores synthetic telemetry, policy evaluation results, cost tracking outputs, and curated reporting tables.

### Power BI Dashboard

Power BI provides dashboards for agent observability, governance status, cost tracking, usage trends, and operational review.

## Data Flow

```text
User -> Agent -> Telemetry -> Policy Engine -> Fabric Lakehouse -> Power BI
```
