#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-8765}"
URL="http://${HOST}:${PORT}"

cd "$REPO_ROOT"

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[INFO] Config UI is already running: ${URL}"
  if command -v open >/dev/null 2>&1; then
    open "${URL}" >/dev/null 2>&1 || true
  fi
  exit 0
fi

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[ERROR] python3 not found. Please install Python 3.11+."
  exit 1
fi

echo "[INFO] Starting Config UI at ${URL}"
echo "[INFO] Press Ctrl+C to stop."

if command -v open >/dev/null 2>&1; then
  (sleep 1; open "${URL}" >/dev/null 2>&1 || true) &
fi

exec "${PYTHON_BIN}" -m src.main config-ui --host "${HOST}" --port "${PORT}"
