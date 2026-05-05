#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/fabric_deploy.sh <workspace-name> [options]

Options:
  --lakehouse-name <name>   Lakehouse item name to validate or create.
                            Default: AgentControlTower
  --create-lakehouse        Create the Lakehouse if it does not exist.
  --upload                  Upload local CSV files to Lakehouse Files.
  --help                    Show this help text.

Examples:
  ./scripts/fabric_deploy.sh "My Fabric Workspace"
  ./scripts/fabric_deploy.sh "My Fabric Workspace" --create-lakehouse --upload

This script uses Microsoft Fabric CLI where possible. It does not delete Fabric
items, pause capacity, resume capacity, or run Spark jobs.
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

WORKSPACE_NAME="$1"
shift

LAKEHOUSE_NAME="AgentControlTower"
CREATE_LAKEHOUSE=false
UPLOAD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lakehouse-name)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --lakehouse-name requires a value." >&2
        exit 1
      fi
      LAKEHOUSE_NAME="$2"
      shift 2
      ;;
    --create-lakehouse)
      CREATE_LAKEHOUSE=true
      shift
      ;;
    --upload)
      UPLOAD=true
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"

WORKSPACE_PATH="${WORKSPACE_NAME}.Workspace"
LAKEHOUSE_PATH="${WORKSPACE_PATH}/${LAKEHOUSE_NAME}.Lakehouse"
RAW_PATH="${LAKEHOUSE_PATH}/Files/agent_control_tower/raw"

required_csv_files=(
  "dim_agent.csv"
  "dim_model.csv"
  "fact_agent_run.csv"
  "fact_policy_breach.csv"
  "fact_feedback.csv"
)

echo "Validating local prerequisites..."

if ! command -v fab >/dev/null 2>&1; then
  echo "ERROR: Fabric CLI is not installed or not on PATH." >&2
  echo "Install it with: pip install ms-fabric-cli" >&2
  exit 1
fi

echo "Checking Fabric CLI authentication..."
if ! fab ls >/dev/null 2>&1; then
  echo "ERROR: Fabric CLI is not authenticated or cannot list workspaces." >&2
  echo "Run: fab auth login" >&2
  exit 1
fi

echo "Checking workspace access: ${WORKSPACE_PATH}"
if ! fab ls "${WORKSPACE_PATH}" >/dev/null 2>&1; then
  echo "ERROR: Cannot access workspace '${WORKSPACE_NAME}'." >&2
  echo "Confirm the workspace name and your Fabric permissions." >&2
  exit 1
fi

echo "Checking local CSV data files..."
for file_name in "${required_csv_files[@]}"; do
  if [[ ! -f "${DATA_DIR}/${file_name}" ]]; then
    echo "ERROR: Missing local data file: ${DATA_DIR}/${file_name}" >&2
    echo "Run: python src/generate_synthetic_agent_runs.py" >&2
    exit 1
  fi
done

echo "Validating Lakehouse item: ${LAKEHOUSE_PATH}"
if fab ls "${LAKEHOUSE_PATH}" >/dev/null 2>&1; then
  echo "Lakehouse exists."
else
  if [[ "${CREATE_LAKEHOUSE}" == "true" ]]; then
    echo "Lakehouse does not exist. Creating: ${LAKEHOUSE_PATH}"
    fab create "${LAKEHOUSE_PATH}"
  else
    echo "Lakehouse does not exist: ${LAKEHOUSE_PATH}"
    echo "Next manual step:"
    echo "  Create a Lakehouse named '${LAKEHOUSE_NAME}' in workspace '${WORKSPACE_NAME}',"
    echo "  or rerun this script with --create-lakehouse if your permissions allow it."
    exit 0
  fi
fi

echo "Target raw data path:"
echo "  ${RAW_PATH}"

if [[ "${UPLOAD}" == "true" ]]; then
  echo "Uploading CSV files to Lakehouse Files..."
  for file_name in "${required_csv_files[@]}"; do
    fab cp "${DATA_DIR}/${file_name}" "${RAW_PATH}/${file_name}"
  done
  echo "CSV upload complete."
else
  echo "Upload not requested."
  echo "Next manual or explicit step:"
  echo "  Rerun with --upload to copy CSVs into:"
  echo "  ${RAW_PATH}"
fi

echo "Next Fabric notebook step:"
echo "  Open notebooks/fabric_load_agent_control_tower.py in a Fabric notebook attached to the Lakehouse."
echo "  Run it to create Delta tables and aggregates."
