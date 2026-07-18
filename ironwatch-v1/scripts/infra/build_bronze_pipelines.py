"""Create, run, and verify the Bronze ingestion Data Pipelines (ADR-002/ADR-007).

One Copy Activity pipeline per source file, landing raw structure into
ironwatch_bronze as Delta tables. No transformation logic here.
"""
from __future__ import annotations

import base64
import json
import sys
import time

import requests
from azure.identity import DefaultAzureCredential

WORKSPACE_ID = "e0bb7021-f3a3-430f-a739-442d4be7a40f"
BRONZE_LAKEHOUSE_ID = "7f1e5fd6-7fbc-4ea1-b31a-fd8baa978349"
LANDING_CONNECTION_ID = "8b72d01d-1f45-4c66-b08c-e5883f6d5184"
FABRIC_API = "https://api.fabric.microsoft.com/v1"

SOURCES = [
    {"pipeline": "pl_bronze_asset_master_load", "activity": "CopyAssetMaster", "file": "asset_master.csv", "format": "csv", "table": "asset_master_raw"},
    {"pipeline": "pl_bronze_telemetry_load", "activity": "CopyTelemetry", "file": "telemetry.parquet", "format": "parquet", "table": "telemetry_raw"},
    {"pipeline": "pl_bronze_fault_codes_load", "activity": "CopyFaultCodes", "file": "fault_codes.json", "format": "json", "table": "fault_codes_raw"},
    {"pipeline": "pl_bronze_service_history_load", "activity": "CopyServiceHistory", "file": "service_history.csv", "format": "csv", "table": "service_history_raw"},
    {"pipeline": "pl_bronze_oil_samples_load", "activity": "CopyOilSamples", "file": "oil_samples.csv", "format": "csv", "table": "oil_samples_raw"},
]


def _token() -> str:
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return cred.get_token("https://api.fabric.microsoft.com/.default").token


def _source_type_properties(fmt: str, file_name: str) -> dict:
    location = {
        "type": "AzureBlobFSLocation",
        "fileName": file_name,
        "fileSystem": "ironwatch-landing",
    }
    dataset_type_properties = {"location": location}

    if fmt == "csv":
        source = {
            "type": "DelimitedTextSource",
            "storeSettings": {"type": "AzureBlobFSReadSettings", "recursive": True},
            "formatSettings": {"type": "DelimitedTextReadSettings"},
        }
        dataset = {
            "annotations": [],
            "type": "DelimitedText",
            "typeProperties": {
                **dataset_type_properties,
                "columnDelimiter": ",",
                "escapeChar": "\\",
                "firstRowAsHeader": True,
                "quoteChar": '"',
            },
            "schema": [],
            "externalReferences": {"connection": LANDING_CONNECTION_ID},
        }
    elif fmt == "json":
        source = {
            "type": "JsonSource",
            "storeSettings": {"type": "AzureBlobFSReadSettings", "recursive": True},
            "formatSettings": {"type": "JsonReadSettings"},
        }
        dataset = {
            "annotations": [],
            "type": "Json",
            "typeProperties": dataset_type_properties,
            "schema": [],
            "externalReferences": {"connection": LANDING_CONNECTION_ID},
        }
    elif fmt == "parquet":
        source = {
            "type": "ParquetSource",
            "storeSettings": {"type": "AzureBlobFSReadSettings", "recursive": True},
        }
        dataset = {
            "annotations": [],
            "type": "Parquet",
            "typeProperties": dataset_type_properties,
            "schema": [],
            "externalReferences": {"connection": LANDING_CONNECTION_ID},
        }
    else:
        raise ValueError(f"Unknown format: {fmt}")

    source["datasetSettings"] = dataset
    return source


def build_pipeline_content(source: dict) -> dict:
    return {
        "name": source["pipeline"],
        "properties": {
            "activities": [
                {
                    "name": source["activity"],
                    "type": "Copy",
                    "dependsOn": [],
                    "policy": {
                        "timeout": "0.12:00:00",
                        "retry": 0,
                        "retryIntervalInSeconds": 30,
                        "secureOutput": False,
                        "secureInput": False,
                    },
                    "typeProperties": {
                        "source": _source_type_properties(source["format"], source["file"]),
                        "sink": {
                            "type": "LakehouseTableSink",
                            "tableActionOption": "Overwrite",
                            "datasetSettings": {
                                "annotations": [],
                                "linkedService": {
                                    "name": "ironwatch_bronze",
                                    "properties": {
                                        "type": "Lakehouse",
                                        "typeProperties": {
                                            "workspaceId": WORKSPACE_ID,
                                            "artifactId": BRONZE_LAKEHOUSE_ID,
                                            "rootFolder": "Tables",
                                        },
                                    },
                                },
                                "type": "LakehouseTable",
                                "schema": [],
                                "typeProperties": {"table": source["table"]},
                            },
                        },
                        "enableStaging": False,
                        "translator": {
                            "type": "TabularTranslator",
                            "typeConversion": True,
                            "typeConversionSettings": {
                                "allowDataTruncation": True,
                                "treatBooleanAsNumber": False,
                            },
                        },
                    },
                    "inputs": [],
                    "outputs": [],
                }
            ]
        },
    }


def create_pipeline_item(token: str, source: dict) -> str:
    content = build_pipeline_content(source)
    payload_b64 = base64.b64encode(json.dumps(content).encode()).decode()
    resp = requests.post(
        f"{FABRIC_API}/workspaces/{WORKSPACE_ID}/items",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "displayName": source["pipeline"],
            "type": "DataPipeline",
            "definition": {"parts": [{"path": "pipeline-content.json", "payload": payload_b64, "payloadType": "InlineBase64"}]},
        },
        timeout=60,
    )
    if resp.status_code == 201:
        return resp.json()["id"]
    print(f"  create failed [{resp.status_code}]: {resp.text}", file=sys.stderr)
    resp.raise_for_status()
    raise RuntimeError("unreachable")


def run_pipeline(token: str, item_id: str) -> str:
    resp = requests.post(
        f"{FABRIC_API}/workspaces/{WORKSPACE_ID}/items/{item_id}/jobs/instances?jobType=Pipeline",
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.headers["Location"].rsplit("/", 1)[-1]


def poll_job(token: str, item_id: str, job_id: str, timeout_s: int = 300) -> dict:
    url = f"{FABRIC_API}/workspaces/{WORKSPACE_ID}/items/{item_id}/jobs/instances/{job_id}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data["status"] in ("Completed", "Failed", "Cancelled", "Deduped"):
            return data
        time.sleep(10)
    raise TimeoutError(f"job {job_id} did not reach terminal state in {timeout_s}s")


def main() -> None:
    token = _token()
    results = []
    for source in SOURCES:
        print(f"=== {source['pipeline']} ({source['file']} -> {source['table']}) ===")
        item_id = create_pipeline_item(token, source)
        print(f"  item created: {item_id}")
        job_id = run_pipeline(token, item_id)
        print(f"  job started: {job_id}")
        job = poll_job(token, item_id, job_id)
        print(f"  job status: {job['status']} (failureReason: {job.get('failureReason')})")
        results.append({"source": source, "item_id": item_id, "job": job})

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['source']['pipeline']}: {r['job']['status']}")


if __name__ == "__main__":
    main()
