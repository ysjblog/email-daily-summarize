#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
CONFIG_FILE="${DAILY_SUMMARIZE_CONFIG:-${REPO_ROOT}/config/settings.local.yaml}"
SECRETS_FILE="${DAILY_SUMMARIZE_ENV_FILE:-${REPO_ROOT}/config/secrets.local.env}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[ERROR] Missing config file: ${CONFIG_FILE}"
  echo "Run ./init-user-config.command first."
  exit 1
fi

if [[ ! -f "${SECRETS_FILE}" ]]; then
  echo "[ERROR] Missing secrets file: ${SECRETS_FILE}"
  echo "Run ./init-secrets.command first."
  exit 1
fi

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[ERROR] python3 not found. Please install Python 3.11+."
  exit 1
fi

ACCOUNT="${1:-}"
EMAIL="${2:-}"

if [[ -z "${ACCOUNT}" ]]; then
  echo "Choose account id (work/personal):"
  read -r ACCOUNT
fi

if [[ -z "${ACCOUNT}" ]]; then
  echo "[ERROR] account id is required"
  exit 1
fi

if [[ -z "${EMAIL}" ]]; then
  echo "Google login hint email (optional, press Enter to skip):"
  read -r EMAIL || true
fi

CMD=("${PYTHON_BIN}" -m src.main --config "${CONFIG_FILE}" --env-file "${SECRETS_FILE}" auth login --account "${ACCOUNT}")
if [[ -n "${EMAIL}" ]]; then
  CMD+=(--email "${EMAIL}")
fi

echo "[INFO] Running OAuth login for account=${ACCOUNT}"
exec "${CMD[@]}"
