#!/usr/bin/env python3
"""
Smoke-test RAG connectors (real HTTP). From repo root:

  PYTHONPATH=packages packages/api/.venv/bin/python scripts/test_connectors.py

(System python often lacks `httpx`; use the API venv.) Keys: same as root `.env` / `packages/api/.env`.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

from rag.connectors.settings import ConnectorSettings  # noqa: E402
from rag.pipeline.runner import build_connectors  # noqa: E402


async def main() -> None:
    entity_id = os.environ.get("CONNECTOR_TEST_ENTITY_ID", "test-entity-001")
    scan_id = os.environ.get("CONNECTOR_TEST_SCAN_ID", "test-scan-001")
    legal_name = os.environ.get("CONNECTOR_TEST_LEGAL_NAME", "DelugeRPG")
    domain = os.environ.get("CONNECTOR_TEST_DOMAIN", "delugerpg.com")

    cs = ConnectorSettings(
        courtlistener_api_key=os.environ.get("COURTLISTENER_API_KEY"),
        github_token=os.environ.get("GITHUB_TOKEN"),
        newsapi_key=os.environ.get("NEWSAPI_KEY"),
        firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY"),
        adzuna_app_id=os.environ.get("ADZUNA_APP_ID"),
        adzuna_api_key=os.environ.get("ADZUNA_API_KEY"),
        adzuna_country=os.environ.get("ADZUNA_COUNTRY", "us"),
    )
    connectors = build_connectors(cs)

    for c in connectors:
        print(f"\n--- {c.connector_id} ---")
        result = await c.fetch_with_retry(entity_id, scan_id, legal_name, domain)
        print(f"  status:      {result.status}")
        print(f"  chunks:      {len(result.chunks)}")
        print(f"  error:       {result.error}")
        if result.chunks:
            preview = result.chunks[0].normalized_text[:120].replace("\n", " ")
            print(f"  first chunk: {preview!r}")


if __name__ == "__main__":
    asyncio.run(main())
