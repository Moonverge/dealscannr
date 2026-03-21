#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/packages"
cd "$ROOT/packages"

VENV_PY="$ROOT/packages/api/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "No API venv at packages/api/.venv" >&2
  echo "Create it once:" >&2
  echo "  cd \"$ROOT/packages/api\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  echo "Then from repo root:" >&2
  echo "  ./scripts/ingest.sh \"Company Name\"" >&2
  exit 1
fi

if ! "$VENV_PY" -c "import qdrant_client" 2>/dev/null; then
  echo "Installing deps into packages/api/.venv …" >&2
  "$VENV_PY" -m pip install -q -r "$ROOT/packages/api/requirements.txt" -r "$ROOT/packages/ingestion/requirements.txt"
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <company name>" >&2
  exit 1
fi
exec "$VENV_PY" -m ingestion "$@"
