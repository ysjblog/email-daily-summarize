#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${DAILY_SUMMARIZE_CONFIG:-${REPO_ROOT}/config/settings.local.yaml}"
SECRETS_FILE="${DAILY_SUMMARIZE_ENV_FILE:-${REPO_ROOT}/config/secrets.local.env}"
LOG_FILE="${REPO_ROOT}/logs/local-scheduler.log"
LOCK_FILE="${REPO_ROOT}/logs/.run_daily_digest.lock"
# 同一排程時間點（以 30 分鐘為窗口）不重複執行
DEDUP_WINDOW_MINUTES=30
STAMP_FILE="${REPO_ROOT}/logs/.last_run_stamp"

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

# ── 防重複執行：時間窗口 stamp 檢查（防止 launchd 補發導致雙重觸發）────────────
NOW_EPOCH=$(date +%s)
if [[ -f "${STAMP_FILE}" ]]; then
  LAST_EPOCH=$(cat "${STAMP_FILE}" 2>/dev/null || echo 0)
  ELAPSED=$(( NOW_EPOCH - LAST_EPOCH ))
  WINDOW_SECS=$(( DEDUP_WINDOW_MINUTES * 60 ))
  if (( ELAPSED < WINDOW_SECS )); then
    echo "[SKIP] $(date '+%Y-%m-%d %H:%M:%S %z') 距離上次執行僅 ${ELAPSED}s（< ${WINDOW_SECS}s），跳過重複觸發。" >> "${LOG_FILE}" 2>&1
    exit 0
  fi
fi
echo "${NOW_EPOCH}" > "${STAMP_FILE}"

source .venv/bin/activate

# ── flock 鎖定：防止並發執行（萬一 stamp 同時通過也守住）────────────────────
(
  flock -n 9 || {
    echo "[SKIP] $(date '+%Y-%m-%d %H:%M:%S %z') 另一個執行緒正在執行，跳過。" >> "${LOG_FILE}" 2>&1
    exit 0
  }
  echo "[INFO] ===== $(date '+%Y-%m-%d %H:%M:%S %z') run start ====="
  echo "[INFO] config=${CONFIG_FILE}"
  python -m src.main --config "${CONFIG_FILE}" --env-file "${SECRETS_FILE}" run
  echo "[INFO] ===== $(date '+%Y-%m-%d %H:%M:%S %z') run end ====="
) 9>"${LOCK_FILE}" >> "${LOG_FILE}" 2>&1
