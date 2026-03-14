#!/usr/bin/env bash
set -euo pipefail
export DAILY_SUMMARIZE_CONFIG="/Applications/Project_exception/daily summerize/config/settings.local.yaml"
export DAILY_SUMMARIZE_ENV_FILE="/Applications/Project_exception/daily summerize/config/secrets.local.env"
cd "/Applications/Project_exception/daily summerize"
exec /bin/bash "/Applications/Project_exception/daily summerize/scripts/run_daily_digest.sh"
