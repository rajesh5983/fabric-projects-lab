"""
Delta-backed execution audit log for IronWatch v1 pipelines.

Every notebook calls log_execution() at pipeline start and end so the
execution_log Delta table carries a complete run history across bronze,
silver, and gold. A bad audit write must never take a pipeline down:
log_execution() always returns a run_id and never raises — write
failures are caught and reported as a warning instead.

This module will become forge_core.audit during IronCore extraction
in July 2026.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from config import get_lakehouse_path

# get_lakehouse_path("gold") resolves to the *Warehouse* item per ADR-001.
# Direct Delta writes into a Warehouse-backed OneLake path are not a
# supported Fabric pattern — confirm during build whether this table
# should instead live under ironwatch_silver and adjust AUDIT_LAYER.
AUDIT_LAYER = "gold"
AUDIT_TABLE_RELATIVE_PATH = "_ironwatch_meta/execution_log"


def _audit_table_path() -> str:
    return f"{get_lakehouse_path(AUDIT_LAYER)}/Tables/{AUDIT_TABLE_RELATIVE_PATH}"


def _active_spark_session():
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        return None
    return SparkSession.getActiveSession()


def _write_with_spark(session, record: dict, table_path: str) -> None:
    from pyspark.sql.types import (
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    schema = StructType([
        StructField("run_id", StringType(), False),
        StructField("pipeline_name", StringType(), False),
        StructField("layer", StringType(), False),
        StructField("status", StringType(), False),
        StructField("rows_processed", LongType(), False),
        StructField("error_message", StringType(), True),
        StructField("engine", StringType(), False),
        StructField("recorded_at", TimestampType(), False),
    ])
    (
        session.createDataFrame([record], schema=schema)
        .write.format("delta")
        .mode("append")
        .save(table_path)
    )


def _write_with_pandas(record: dict, table_path: str) -> None:
    import pandas as pd
    import pyarrow as pa
    from deltalake import write_deltalake

    # An explicit schema is required: error_message is None on success
    # records, and pandas/pyarrow would otherwise infer that all-null
    # column as Delta's unwritable "null" type.
    schema = pa.schema([
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("pipeline_name", pa.string(), nullable=False),
        pa.field("layer", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("rows_processed", pa.int64(), nullable=False),
        pa.field("error_message", pa.string(), nullable=True),
        pa.field("engine", pa.string(), nullable=False),
        pa.field("recorded_at", pa.timestamp("us", tz="UTC"), nullable=False),
    ])
    table = pa.Table.from_pandas(pd.DataFrame([record]), schema=schema, preserve_index=False)
    write_deltalake(table_path, table, mode="append")


def log_execution(
    pipeline_name: str,
    layer: str,
    status: str,
    rows_processed: int = 0,
    error_message: Optional[str] = None,
    engine: str = "spark",
) -> str:
    """Record one pipeline execution event and return its run_id.

    Always returns a run_id, even if the underlying audit write fails —
    callers can rely on log_execution() never raising.
    """
    run_id = str(uuid.uuid4())

    try:
        record = {
            "run_id": run_id,
            "pipeline_name": pipeline_name,
            "layer": layer,
            "status": status,
            "rows_processed": int(rows_processed),
            "error_message": error_message,
            "engine": engine,
            "recorded_at": datetime.now(timezone.utc),
        }
        table_path = _audit_table_path()

        session = _active_spark_session()
        if session is not None:
            _write_with_spark(session, record, table_path)
        else:
            _write_with_pandas(record, table_path)
    except Exception as exc:
        # str(exc) can contain characters the host console can't encode
        # (e.g. delta-rs error messages use non-ASCII arrows). Sanitize
        # before printing so a warning about a failed write can never
        # itself raise and break the "log_execution never raises" contract.
        safe_detail = str(exc).encode("ascii", errors="backslashreplace").decode("ascii")
        print(
            f"WARNING: audit log write failed "
            f"(run_id={run_id}, pipeline={pipeline_name}, layer={layer}, status={status}): {safe_detail}"
        )

    return run_id
