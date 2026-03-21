#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/packages/api"

if [[ ! -d .venv ]]; then
  echo "Creating virtualenv at packages/api/.venv …"
  python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install -q --upgrade pip
python -m pip install -r requirements.txt

export PYTHONPATH="$ROOT/packages"
exec uvicorn main:app --reload --port 5200
