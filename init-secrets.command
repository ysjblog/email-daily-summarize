#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
TARGET_DIR="${HOME}/.config/daily-summarize"
TARGET_FILE="${TARGET_DIR}/secrets.env"
SOURCE_FILE="${REPO_ROOT}/config/secrets.example.env"

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "[ERROR] Missing template: ${SOURCE_FILE}"
  exit 1
fi

mkdir -p "${TARGET_DIR}"

if [[ ! -f "${TARGET_FILE}" ]]; then
  cp "${SOURCE_FILE}" "${TARGET_FILE}"
  echo "[OK] Created secrets file: ${TARGET_FILE}"
else
  echo "[INFO] Secrets file already exists: ${TARGET_FILE}"
fi

chmod 600 "${TARGET_FILE}"
echo "[OK] Applied secure permission: 600"
echo "[NEXT] Fill your real tokens in ${TARGET_FILE}"
