#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_FILE="${HOME}/.config/daily-summarize/secrets.env"

cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Please install Python 3.11+ first."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "[INFO] Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "[INFO] Installing dependencies..."
pip install -r requirements.txt >/dev/null

if [[ ! -f "${SECRETS_FILE}" ]]; then
  echo "[ERROR] Missing secrets file: ${SECRETS_FILE}"
  echo "Create it with:"
  echo "  mkdir -p ~/.config/daily-summarize"
  echo "  cp config/secrets.example.env ~/.config/daily-summarize/secrets.env"
  echo "  chmod 600 ~/.config/daily-summarize/secrets.env"
  exit 1
fi

perm="$(stat -f '%Lp' "${SECRETS_FILE}")"
if [[ "${perm}" != "600" ]]; then
  echo "[ERROR] Insecure permission on ${SECRETS_FILE} (current: ${perm})"
  echo "Fix with: chmod 600 ${SECRETS_FILE}"
  exit 1
fi

python - <<'PY'
import os
import sys

from src.config import load_settings
from src.env_utils import parse_env_file

settings = load_settings("config/settings.yaml")
env = parse_env_file(os.path.expanduser("~/.config/daily-summarize/secrets.env"))
missing = []

for account in settings.enabled_accounts():
    prefix = account.env_prefix.upper()
    for suffix in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
        key = f"{prefix}_{suffix}"
        if not env.get(key):
            missing.append(key)

channels = settings.digest.get("channels", ["gmail"])
if "slack_bot" in channels and not env.get("SLACK_BOT_TOKEN"):
    missing.append("SLACK_BOT_TOKEN")

if "line" in channels:
    if not env.get("LINE_CHANNEL_ACCESS_TOKEN"):
        missing.append("LINE_CHANNEL_ACCESS_TOKEN")
    line_cfg = settings.digest.get("line", {})
    if line_cfg.get("enabled") and not (env.get("LINE_TARGET_USER_ID") or line_cfg.get("target_user_id")):
        missing.append("LINE_TARGET_USER_ID (or digest.line.target_user_id in config/settings.yaml)")

if missing:
    print("[ERROR] Missing required secrets:")
    for key in missing:
        print(f"- {key}")
    sys.exit(1)
PY

echo "[INFO] Running dry-run..."
python -m src.main dry-run --env-file "${SECRETS_FILE}"

echo "[DONE] Dry-run completed."
echo "Run production mode with: python -m src.main run --env-file ${SECRETS_FILE}"
