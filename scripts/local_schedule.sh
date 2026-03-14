#!/usr/bin/env bash
set -euo pipefail

LABEL="com.daily-summarize.digest"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# plist 必須安裝到 ~/Library/LaunchAgents（macOS launchd 標準路徑）
# 外部磁碟路徑 launchd 會因 ownership 問題拒絕 load（見 lessons.md）
SYSTEM_USER="$(id -un)"
LAUNCHAGENTS_DIR="/Users/${SYSTEM_USER}/Library/LaunchAgents"
PLIST_INSTALL_PATH="${LAUNCHAGENTS_DIR}/${LABEL}.plist"
PLIST_REPO_PATH="${REPO_ROOT}/${LABEL}.plist"  # repo 內備份用
RUN_SCRIPT="${REPO_ROOT}/scripts/run_daily_digest.sh"
LAUNCHD_RUNNER_DIR="${REPO_ROOT}/logs/launchd_runner"
LAUNCHD_RUNNER_PATH="${LAUNCHD_RUNNER_DIR}/run_daily_digest.sh"
LAUNCHD_LOG_DIR="${REPO_ROOT}/logs"
# launchd plist 的 log 必須在系統原生路徑（外部磁碟路徑在 bootstrap 時可能未 mount）
LAUNCHD_SYS_LOG_DIR="/Users/${SYSTEM_USER}/Library/Logs/DailySummarize"
SYSTEM_HOME="/Users/${SYSTEM_USER}"
CONFIG_FILE="${DAILY_SUMMARIZE_CONFIG:-${REPO_ROOT}/config/settings.local.yaml}"
SECRETS_FILE="${DAILY_SUMMARIZE_ENV_FILE:-${REPO_ROOT}/config/secrets.local.env}"

RUN_TIMES=()

read_run_times() {
  local output
  output="$(DAILY_SUMMARIZE_CONFIG="${CONFIG_FILE}" "${REPO_ROOT}/.venv/bin/python" - <<'PY'
import os
import re

from src.config import load_settings

config_path = os.path.expanduser(os.environ["DAILY_SUMMARIZE_CONFIG"])
settings = load_settings(config_path)
if not settings.run_times:
    raise SystemExit("run_times is empty in config file")

for value in settings.run_times:
    text = str(value).strip()
    if not re.fullmatch(r"\d{2}:\d{2}", text):
        raise SystemExit(f"invalid run_time format: {text}")
    hour, minute = (int(part) for part in text.split(":", 1))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise SystemExit(f"invalid run_time value: {text}")
    print(f"{hour:02d}:{minute:02d}")
PY
)"

  RUN_TIMES=()
  while IFS= read -r line; do
    [[ -n "${line}" ]] && RUN_TIMES+=("${line}")
  done <<< "${output}"
}

build_schedule_xml() {
  local result=""
  local item hour minute
  for item in "${RUN_TIMES[@]}"; do
    hour="${item%%:*}"
    minute="${item##*:}"
    result+="    <dict>\n"
    result+="      <key>Hour</key>\n"
    result+="      <integer>$((10#${hour}))</integer>\n"
    result+="      <key>Minute</key>\n"
    result+="      <integer>$((10#${minute}))</integer>\n"
    result+="    </dict>\n"
  done
  printf "%b" "${result}"
}

require_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[ERROR] local_schedule.sh only supports macOS launchd."
    exit 1
  fi
}

check_prerequisites() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Please install Python 3.11+."
    exit 1
  fi

  if [[ ! -x "${RUN_SCRIPT}" ]]; then
    echo "[ERROR] Missing run script: ${RUN_SCRIPT}"
    exit 1
  fi

  if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    echo "[ERROR] .venv not found. Run: bash scripts/quickstart.sh"
    exit 1
  fi

  if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "[ERROR] Missing config file: ${CONFIG_FILE}"
    exit 1
  fi

  if [[ ! -f "${SECRETS_FILE}" ]]; then
    echo "[ERROR] Missing secrets file: ${SECRETS_FILE}"
    exit 1
  fi

  local perm
  perm="$(stat -f '%Lp' "${SECRETS_FILE}")"
  if [[ "${perm}" != "600" ]]; then
    echo "[ERROR] Insecure permission on ${SECRETS_FILE} (current: ${perm})"
    echo "[ERROR] Fix with: chmod 600 ${SECRETS_FILE}"
    exit 1
  fi
}

write_runner_script() {
  mkdir -p "${LAUNCHD_RUNNER_DIR}"
  cat > "${LAUNCHD_RUNNER_PATH}" <<EOF_RUNNER
#!/usr/bin/env bash
set -euo pipefail
export DAILY_SUMMARIZE_CONFIG="${CONFIG_FILE}"
export DAILY_SUMMARIZE_ENV_FILE="${SECRETS_FILE}"
cd "${REPO_ROOT}"
exec /bin/bash "${RUN_SCRIPT}"
EOF_RUNNER
  chmod 755 "${LAUNCHD_RUNNER_PATH}"
}

write_plist() {
  mkdir -p "${REPO_ROOT}/logs" "${LAUNCHD_LOG_DIR}" "${LAUNCHAGENTS_DIR}" "${LAUNCHD_SYS_LOG_DIR}"
  read_run_times
  write_runner_script

  local plist_content
  plist_content="$(cat <<EOF_PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${LAUNCHD_RUNNER_PATH}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${SYSTEM_HOME}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key>
    <string>Asia/Taipei</string>
    <key>DAILY_SUMMARIZE_CONFIG</key>
    <string>${CONFIG_FILE}</string>
    <key>DAILY_SUMMARIZE_ENV_FILE</key>
    <string>${SECRETS_FILE}</string>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StartCalendarInterval</key>
  <array>
$(build_schedule_xml)
  </array>
  <key>StandardOutPath</key>
  <string>${LAUNCHD_SYS_LOG_DIR}/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LAUNCHD_SYS_LOG_DIR}/launchd.err.log</string>
</dict>
</plist>
EOF_PLIST
)"
  # 同時寫到 repo（備份）和 ~/Library/LaunchAgents（系統正式路徑）
  printf '%s\n' "${plist_content}" > "${PLIST_REPO_PATH}"
  printf '%s\n' "${plist_content}" > "${PLIST_INSTALL_PATH}"
  chmod 644 "${PLIST_INSTALL_PATH}"
}

# ── cron tag （方便識別與移除）──────────────────────────────────────────
CRON_TAG="# daily-summarize-digest-managed"

build_cron_entries() {
  local item hour minute entries=""
  for item in "${RUN_TIMES[@]}"; do
    hour="${item%%:*}"
    minute="${item##*:}"
    entries+="${minute} ${hour} * * * /bin/bash '${LAUNCHD_RUNNER_PATH}' >> '${LAUNCHD_LOG_DIR}/cron.out.log' 2>> '${LAUNCHD_LOG_DIR}/cron.err.log' ${CRON_TAG}\n"
  done
  printf '%b' "${entries}"
}

start_schedule() {
  require_macos
  check_prerequisites
  read_run_times
  write_runner_script
  # 備份寫 plist（不再用 launchctl load，因外部磁碟 symlink 導致 Error 5）
  write_plist > /dev/null 2>&1 || true

  # 移除舊的 cron，再寫入新的
  local existing new_entry
  existing="$(crontab -l 2>/dev/null | grep -v "${CRON_TAG}" || true)"
  new_entry="$(build_cron_entries)"
  printf '%s\n%b' "${existing}" "${new_entry}" | grep -v '^$' | sort -u | crontab -

  echo "[OK] Cron schedule started."
  echo "[INFO] Runner: ${LAUNCHD_RUNNER_PATH}"
  echo "[INFO] Config: ${CONFIG_FILE}"
  echo "[INFO] Times (Asia/Taipei): ${RUN_TIMES[*]}"
  echo "[INFO] Cron entries:"
  crontab -l | grep "${CRON_TAG}" || true
}

stop_schedule() {
  require_macos
  local existing
  existing="$(crontab -l 2>/dev/null | grep -v "${CRON_TAG}" || true)"
  if [[ -z "${existing}" ]]; then
    crontab -r 2>/dev/null || true
  else
    printf '%s\n' "${existing}" | crontab -
  fi
  echo "[OK] Cron schedule stopped."
}

status_schedule() {
  require_macos
  read_run_times
  local active
  active="$(crontab -l 2>/dev/null | grep "${CRON_TAG}" || true)"
  if [[ -n "${active}" ]]; then
    echo "[OK] Cron schedule is ACTIVE."
    echo "${active}"
  else
    echo "[WARN] Cron schedule is NOT set."
  fi
  echo "[INFO] Config: ${CONFIG_FILE}"
  echo "[INFO] Times (Asia/Taipei): ${RUN_TIMES[*]}"
  echo "[INFO] Log dir: ${LAUNCHD_LOG_DIR}"
}

run_now() {
  check_prerequisites
  DAILY_SUMMARIZE_CONFIG="${CONFIG_FILE}" DAILY_SUMMARIZE_ENV_FILE="${SECRETS_FILE}" exec "${RUN_SCRIPT}"
}

usage() {
  echo "Usage: bash scripts/local_schedule.sh {start|stop|status|run-now}"
}

main() {
  case "${1:-}" in
    start) start_schedule ;;
    stop) stop_schedule ;;
    status) status_schedule ;;
    run-now) run_now ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
