#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
TARGET_DIR="${REPO_ROOT}/config"
TARGET_FILE="${TARGET_DIR}/settings.local.yaml"
SOURCE_FILE="${REPO_ROOT}/config/settings.example.yaml"

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "[ERROR] Missing template: ${SOURCE_FILE}"
  exit 1
fi

mkdir -p "${TARGET_DIR}"

if [[ -f "${TARGET_FILE}" ]]; then
  echo "[INFO] Config already exists: ${TARGET_FILE}"
  echo "[INFO] Keep existing file."
  exit 0
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"
echo "[OK] Created config: ${TARGET_FILE}"
echo "[NEXT] Edit this file before running quickstart."
