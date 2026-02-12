#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "${REPO_ROOT}"

exec bash scripts/local_schedule.sh status
