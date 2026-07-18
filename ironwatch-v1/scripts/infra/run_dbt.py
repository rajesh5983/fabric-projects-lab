"""Run `dbt run` for Silver or Gold and log exactly one execution_log record (ADR-010).

dbt models are SQL — a `dbt run` cannot call audit.py's log_execution()
itself. This wrapper invokes dbt as a subprocess, parses the resulting
run_results.json for final status and row count, and logs a single record
after the run completes. log_execution() is append-only (a new run_id via
uuid.uuid4() on every call, no update/correlation mechanism — see ADR-010's
"Audit table contract"), so there is deliberately no call before the run
starts, only after it finishes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from audit import log_execution  # noqa: E402

DBT_PROJECT_DIR = Path(__file__).resolve().parents[2] / "transform" / "ironwatch_gold"
VALID_LAYERS = ("silver", "gold")


def _run_dbt(subcommand: str, target: str) -> int:
    cmd = [
        "dbt", subcommand,
        "--target", target,
        "--profiles-dir", str(DBT_PROJECT_DIR),
        "--project-dir", str(DBT_PROJECT_DIR),
    ]
    result = subprocess.run(cmd, cwd=DBT_PROJECT_DIR)
    return result.returncode


def _parse_run_results() -> tuple[str, int]:
    """Return (status, rows_processed) from the most recent run_results.json.

    adapter_response.rows_affected is -1 for CREATE TABLE AS SELECT
    statements (the ODBC driver doesn't report a meaningful row count for
    DDL/CTAS) — which is what every `table`-materialized model here uses
    per dbt_project.yml. -1 is treated as "not reported" and counted as 0
    rather than propagated as a negative number.
    """
    run_results_path = DBT_PROJECT_DIR / "target" / "run_results.json"
    if not run_results_path.exists():
        return "failed", 0

    data = json.loads(run_results_path.read_text())
    results = data.get("results", [])
    if not results:
        return "failed", 0

    all_success = all(r.get("status") == "success" for r in results)
    rows_processed = 0
    for r in results:
        adapter_response = r.get("adapter_response") or {}
        rows_affected = adapter_response.get("rows_affected")
        if isinstance(rows_affected, int) and rows_affected > 0:
            rows_processed += rows_affected

    return ("success" if all_success else "failed"), rows_processed


def run_and_log(layer: str, target: str, run_tests: bool = False) -> str:
    """Run `dbt run` (and optionally `dbt test`) against `target`, then log exactly one execution_log record for `layer`."""
    if layer not in VALID_LAYERS:
        raise ValueError(f"layer must be one of {VALID_LAYERS}, got {layer!r}")

    run_exit_code = _run_dbt("run", target)
    status, rows_processed = _parse_run_results()

    error_message: Optional[str] = None
    if run_exit_code != 0 and status == "success":
        # dbt run itself failed before any model result was recorded
        # (e.g. a compilation error) — run_results.json may be stale or
        # absent, so don't trust a "success" parsed from it.
        status = "failed"
        error_message = f"dbt run exited {run_exit_code} with no usable run_results.json"

    if run_tests and status == "success":
        test_exit_code = _run_dbt("test", target)
        if test_exit_code != 0:
            status = "failed"
            error_message = "dbt run succeeded but dbt test failed"

    run_id = log_execution(
        pipeline_name=f"dbt_run_{layer}",
        layer=layer,
        status=status,
        rows_processed=rows_processed,
        error_message=error_message,
        engine="dbt-fabric",
    )
    print(
        f"Logged execution_log record: run_id={run_id} layer={layer} "
        f"status={status} rows_processed={rows_processed}"
    )
    return run_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run dbt for a given IronWatch layer and log exactly one audit record afterward."
    )
    parser.add_argument("layer", choices=VALID_LAYERS)
    parser.add_argument(
        "--target",
        default=None,
        help="dbt target name (defaults to the layer name for silver, 'dev' for gold)",
    )
    parser.add_argument(
        "--test", action="store_true", help="Also run `dbt test` after a successful `dbt run`"
    )
    args = parser.parse_args()

    target = args.target or ("dev" if args.layer == "gold" else args.layer)
    run_and_log(args.layer, target, run_tests=args.test)


if __name__ == "__main__":
    main()
