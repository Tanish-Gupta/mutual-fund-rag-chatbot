#!/usr/bin/env bash
# Daily Phase 5 job: ingest seed URLs + rebuild vector index (Chroma by default).
# Intended for cron or launchd at 12:00 local time.
#
# Optional env:
#   MF_PIPELINE_BROWSER=1  — use Playwright for fetch (if plain HTTP hits Cloudflare)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pipeline-$(date +%Y%m%d-%H%M%S).log"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PY="$ROOT/.venv/bin/python3"
elif [[ -x "$ROOT/venv/bin/python3" ]]; then
  PY="$ROOT/venv/bin/python3"
else
  PY="${PYTHON:-python3}"
fi

export PYTHONPATH="$ROOT/phase1/src:$ROOT/phase2/src:$ROOT/phase3/src:$ROOT/phase5/src"

ARGS=(--index-backend chroma)
if [[ "${MF_PIPELINE_BROWSER:-}" == "1" ]]; then
  ARGS+=(--browser)
fi

{
  echo "=== $(date -u +"%Y-%m-%dT%H:%M:%SZ") UTC | mf-rag daily pipeline ==="
  echo "python: $PY"
  echo "args: ${ARGS[*]}"
  "$PY" -m mf_pipeline "${ARGS[@]}"
  echo "=== exit 0 ==="
} >>"$LOG_FILE" 2>&1

exit 0
