"""Generate synthetic telemetry for the AI Agent Control Tower MVP.

This script creates local CSV files only. It does not connect to Fabric or any
external service, and it does not use real customer or operational data.
"""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar
from uuid import uuid4


RUN_COUNT = 2_000
RANDOM_SEED = 42

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
T = TypeVar("T")


@dataclass(frozen=True)
class Agent:
    agent_id: str
    agent_name: str
    business_domain: str
    owner_team: str


@dataclass(frozen=True)
class Model:
    model_id: str
    model_name: str
    provider: str
    cost_per_1k_input_tokens_aud: float
    cost_per_1k_output_tokens_aud: float


AGENTS = [
    Agent("agent_hr_policy", "HR Policy Agent", "Human Resources", "People Operations"),
    Agent(
        "agent_invoice_dispute",
        "Invoice Dispute Agent",
        "Finance Operations",
        "Accounts Receivable",
    ),
    Agent(
        "agent_powerbi_optimiser",
        "Power BI Optimiser Agent",
        "Analytics",
        "Business Intelligence",
    ),
]

MODELS = [
    Model("model_gpt_4o_mini", "gpt-4o-mini", "OpenAI", 0.00025, 0.00100),
    Model("model_gpt_4_1", "gpt-4.1", "OpenAI", 0.00300, 0.01200),
    Model("model_claude_sonnet", "claude-sonnet", "Anthropic", 0.00450, 0.02250),
    Model("model_local_gemma", "local-gemma", "Local", 0.00005, 0.00005),
]

DATA_SOURCES_BY_AGENT = {
    "HR Policy Agent": [
        "HR policy knowledge base",
        "employee handbook",
        "leave policy index",
        "synthetic employee case notes",
    ],
    "Invoice Dispute Agent": [
        "invoice ledger extract",
        "payment dispute queue",
        "vendor contract summary",
        "synthetic customer account notes",
    ],
    "Power BI Optimiser Agent": [
        "Power BI usage metrics",
        "semantic model metadata",
        "DAX performance logs",
        "capacity utilisation extract",
    ],
}

BREACH_COMMENTS = {
    "Run Failure": "Run did not complete and requires operational review.",
    "Low Groundedness": "Response confidence fell below the accepted governance threshold.",
    "High Cost": "Run exceeded the expected cost band for this agent workflow.",
    "Data Risk": "Run used a sensitive synthetic source in a production-like environment.",
}

FEEDBACK_COMMENTS = {
    "positive": [
        "Response was useful and aligned with the request.",
        "Agent completed the task with clear supporting detail.",
        "Output was easy to validate and ready for review.",
    ],
    "neutral": [
        "Response was acceptable but needed light refinement.",
        "Agent completed the task with some manual follow-up.",
        "Output was partially useful for the reviewer.",
    ],
    "negative": [
        "Response missed key context and needed rework.",
        "Agent output was not sufficient for the task.",
        "Reviewer could not rely on the generated answer.",
    ],
}


def weighted_choice(values: list[T], weights: list[float]) -> T:
    return random.choices(values, weights=weights, k=1)[0]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def calculate_cost(input_tokens: int, output_tokens: int, model: Model) -> float:
    input_cost = (input_tokens / 1_000) * model.cost_per_1k_input_tokens_aud
    output_cost = (output_tokens / 1_000) * model.cost_per_1k_output_tokens_aud
    return round(input_cost + output_cost, 4)


def build_dim_agent() -> list[dict[str, object]]:
    return [
        {
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "business_domain": agent.business_domain,
            "owner_team": agent.owner_team,
            "active_flag": True,
        }
        for agent in AGENTS
    ]


def build_dim_model() -> list[dict[str, object]]:
    return [
        {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "provider": model.provider,
            "cost_per_1k_input_tokens_aud": model.cost_per_1k_input_tokens_aud,
            "cost_per_1k_output_tokens_aud": model.cost_per_1k_output_tokens_aud,
        }
        for model in MODELS
    ]


def select_breach_type(
    status: str,
    groundedness_score: float,
    estimated_cost_aud: float,
    data_source_used: str,
    environment: str,
) -> str | None:
    possible_breaches: list[str] = []

    if status != "success":
        possible_breaches.append("Run Failure")
    if groundedness_score < 0.62:
        possible_breaches.append("Low Groundedness")
    if estimated_cost_aud >= 0.08:
        possible_breaches.append("High Cost")
    if environment == "prod" and any(
        marker in data_source_used.lower() for marker in ["employee", "customer", "ledger"]
    ):
        possible_breaches.append("Data Risk")

    if not possible_breaches:
        return None

    return random.choice(possible_breaches)


def derive_risk_level(policy_breach_type: str | None, groundedness_score: float, cost: float) -> str:
    if policy_breach_type in {"Data Risk", "Low Groundedness"} or groundedness_score < 0.55:
        return "high"
    if policy_breach_type in {"High Cost", "Run Failure"} or cost >= 0.06:
        return "medium"
    return "low"


def generate_timestamps() -> list[datetime]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=90)
    total_seconds = int((now - start).total_seconds())
    offsets = sorted(random.randint(0, total_seconds) for _ in range(RUN_COUNT))
    return [start + timedelta(seconds=offset) for offset in offsets]


def generate_agent_runs() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    random.seed(RANDOM_SEED)

    runs: list[dict[str, object]] = []
    breaches: list[dict[str, object]] = []
    feedback: list[dict[str, object]] = []

    for index, timestamp in enumerate(generate_timestamps(), start=1):
        agent = weighted_choice(AGENTS, [0.34, 0.38, 0.28])
        model = weighted_choice(MODELS, [0.55, 0.22, 0.15, 0.08])
        environment = weighted_choice(["dev", "test", "prod"], [0.20, 0.25, 0.55])
        status = weighted_choice(["success", "failed", "timeout", "cancelled"], [0.90, 0.06, 0.03, 0.01])

        input_tokens = int(max(80, random.lognormvariate(7.35, 0.55)))
        output_tokens = int(max(50, random.lognormvariate(6.45, 0.55)))

        if model.model_name in {"gpt-4.1", "claude-sonnet"} and random.random() < 0.18:
            input_tokens = int(input_tokens * random.uniform(1.8, 3.4))
            output_tokens = int(output_tokens * random.uniform(1.5, 2.8))

        latency_base = {
            "gpt-4o-mini": 950,
            "gpt-4.1": 1_850,
            "claude-sonnet": 2_150,
            "local-gemma": 700,
        }[model.model_name]
        latency_ms = int(max(200, random.gauss(latency_base, latency_base * 0.35)))
        if status in {"timeout", "failed"}:
            latency_ms = int(latency_ms * random.uniform(1.8, 4.2))

        groundedness_score = clamp(random.gauss(0.84, 0.11), 0.25, 0.99)
        if random.random() < 0.09:
            groundedness_score = clamp(random.gauss(0.52, 0.10), 0.20, 0.68)

        user_feedback = weighted_choice(
            ["positive", "neutral", "negative", "not_provided"],
            [0.54, 0.24, 0.08, 0.14],
        )
        if status != "success":
            user_feedback = weighted_choice(["negative", "neutral", "not_provided"], [0.48, 0.20, 0.32])

        estimated_cost_aud = calculate_cost(input_tokens, output_tokens, model)
        data_source_used = random.choice(DATA_SOURCES_BY_AGENT[agent.agent_name])
        policy_breach_type = select_breach_type(
            status,
            groundedness_score,
            estimated_cost_aud,
            data_source_used,
            environment,
        )
        risk_level = derive_risk_level(policy_breach_type, groundedness_score, estimated_cost_aud)
        run_id = f"run_{index:06d}_{uuid4().hex[:8]}"
        timestamp_text = timestamp.isoformat()

        runs.append(
            {
                "run_id": run_id,
                "timestamp": timestamp_text,
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "business_domain": agent.business_domain,
                "model_used": model.model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_aud": estimated_cost_aud,
                "latency_ms": latency_ms,
                "status": status,
                "risk_level": risk_level,
                "groundedness_score": round(groundedness_score, 3),
                "user_feedback": user_feedback,
                "policy_breach_type": policy_breach_type or "",
                "tool_calls_count": max(0, min(9, math.floor(random.expovariate(1 / 2.1)))),
                "data_source_used": data_source_used,
                "environment": environment,
            }
        )

        if policy_breach_type:
            breaches.append(
                {
                    "breach_id": f"breach_{len(breaches) + 1:06d}",
                    "run_id": run_id,
                    "timestamp": timestamp_text,
                    "agent_id": agent.agent_id,
                    "policy_breach_type": policy_breach_type,
                    "severity": risk_level,
                    "breach_description": BREACH_COMMENTS[policy_breach_type],
                    "requires_review": risk_level in {"medium", "high"},
                    "environment": environment,
                }
            )

        if user_feedback != "not_provided":
            score_by_feedback = {
                "positive": weighted_choice([4, 5], [0.30, 0.70]),
                "neutral": weighted_choice([3, 4], [0.80, 0.20]),
                "negative": weighted_choice([1, 2], [0.45, 0.55]),
            }
            feedback.append(
                {
                    "feedback_id": f"feedback_{len(feedback) + 1:06d}",
                    "run_id": run_id,
                    "timestamp": timestamp_text,
                    "agent_id": agent.agent_id,
                    "user_feedback": user_feedback,
                    "feedback_score": score_by_feedback[user_feedback],
                    "feedback_comment": random.choice(FEEDBACK_COMMENTS[user_feedback]),
                }
            )

    return runs, breaches, feedback


def write_csv(filename: str, rows: list[dict[str, object]]) -> int:
    path = DATA_DIR / filename
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def write_outputs() -> dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fact_agent_run, fact_policy_breach, fact_feedback = generate_agent_runs()

    outputs = {
        "dim_agent.csv": build_dim_agent(),
        "dim_model.csv": build_dim_model(),
        "fact_agent_run.csv": fact_agent_run,
        "fact_policy_breach.csv": fact_policy_breach,
        "fact_feedback.csv": fact_feedback,
    }

    return {filename: write_csv(filename, rows) for filename, rows in outputs.items()}


def main() -> None:
    row_counts = write_outputs()
    print("Synthetic telemetry CSV files generated:")
    for filename, count in row_counts.items():
        print(f"- {filename}: {count} rows")


if __name__ == "__main__":
    main()
