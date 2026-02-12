#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${DAILY_SUMMARIZE_CONFIG:-${REPO_ROOT}/config/settings.local.yaml}"
SECRETS_FILE="${DAILY_SUMMARIZE_ENV_FILE:-${REPO_ROOT}/config/secrets.local.env}"
LOG_FILE="${REPO_ROOT}/logs/local-scheduler.log"

cd "${REPO_ROOT}"
mkdir -p logs

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Please install Python 3.11+." | tee -a "${LOG_FILE}"
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[ERROR] .venv not found. Run: bash scripts/quickstart.sh" | tee -a "${LOG_FILE}"
  exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[ERROR] Missing config file: ${CONFIG_FILE}" | tee -a "${LOG_FILE}"
  exit 1
fi

if [[ ! -f "${SECRETS_FILE}" ]]; then
  echo "[ERROR] Missing secrets file: ${SECRETS_FILE}" | tee -a "${LOG_FILE}"
  exit 1
fi

perm="$(stat -f '%Lp' "${SECRETS_FILE}")"
if [[ "${perm}" != "600" ]]; then
  echo "[ERROR] Insecure permission on ${SECRETS_FILE} (current: ${perm})" | tee -a "${LOG_FILE}"
  echo "[ERROR] Fix with: chmod 600 ${SECRETS_FILE}" | tee -a "${LOG_FILE}"
  exit 1
fi

source .venv/bin/activate

{
  echo "[INFO] ===== $(date '+%Y-%m-%d %H:%M:%S %z') run start ====="
  echo "[INFO] config=${CONFIG_FILE}"
  python -m src.main --config "${CONFIG_FILE}" --env-file "${SECRETS_FILE}" run
  echo "[INFO] ===== $(date '+%Y-%m-%d %H:%M:%S %z') run end ====="
} >> "${LOG_FILE}" 2>&1
