#!/usr/bin/env bash
set -euo pipefail

LABEL="com.daily-summarize.digest"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
RUN_SCRIPT="${REPO_ROOT}/scripts/run_daily_digest.sh"
SECRETS_FILE="${HOME}/.config/daily-summarize/secrets.env"

RUN_TIMES=()

read_run_times() {
  local output
  output="$(cd "${REPO_ROOT}" && python3 - <<'PY'
import re
from src.config import load_settings

settings = load_settings("config/settings.yaml")
if not settings.run_times:
    raise SystemExit("run_times is empty in config/settings.yaml")

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

write_plist() {
  mkdir -p "${HOME}/Library/LaunchAgents" "${REPO_ROOT}/logs"
  read_run_times

  cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${RUN_SCRIPT}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key>
    <string>Asia/Taipei</string>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StartCalendarInterval</key>
  <array>
$(build_schedule_xml)
  </array>
  <key>StandardOutPath</key>
  <string>${REPO_ROOT}/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${REPO_ROOT}/logs/launchd.err.log</string>
</dict>
</plist>
EOF
}

start_schedule() {
  require_macos
  check_prerequisites
  write_plist
  launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
  launchctl load "${PLIST_PATH}"
  echo "[OK] Local schedule started."
  echo "[INFO] Plist: ${PLIST_PATH}"
  echo "[INFO] Times (Asia/Taipei): ${RUN_TIMES[*]}"
}

stop_schedule() {
  require_macos
  if [[ -f "${PLIST_PATH}" ]]; then
    launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
  fi
  echo "[OK] Local schedule stopped."
}

status_schedule() {
  require_macos
  read_run_times
  if launchctl list | grep -Fq "${LABEL}"; then
    echo "[OK] Local schedule is running."
  else
    echo "[INFO] Local schedule is not running."
  fi
  if [[ -f "${PLIST_PATH}" ]]; then
    echo "[INFO] Plist exists: ${PLIST_PATH}"
  else
    echo "[INFO] Plist not found: ${PLIST_PATH}"
  fi
  echo "[INFO] Times (Asia/Taipei): ${RUN_TIMES[*]}"
}

run_now() {
  check_prerequisites
  exec "${RUN_SCRIPT}"
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
