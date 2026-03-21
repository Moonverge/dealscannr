# DealScannr API

FastAPI service on port **5200** by default.

## Setup

```bash
cd packages/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## PYTHONPATH

The app imports sibling packages `rag` and `ingestion`. From repo root:

```bash
export PYTHONPATH="$(pwd)/packages"
```

Or: `PYTHONPATH=../..` when your cwd is `packages/api` and `packages` is two levels up from `api` — use the absolute parent of `packages` that contains both `api/` and `rag/`.

## Run

```bash
cd packages/api
source .venv/bin/activate
export PYTHONPATH=/path/to/repo/packages
uvicorn main:app --reload --port 5200
```

## PDF export (WeasyPrint)

Python wheels may still need system libraries on Linux, e.g. Debian/Ubuntu:

`libpango-1.0-0`, `libharfbuzz0b`, `libfontconfig1` (and often `libcairo2`).

## Tests

API integration tests live under `../../e2e/api` and expect MongoDB (e.g. Docker on port 5300). See repo root `README.md` and `e2e/README.md`.
