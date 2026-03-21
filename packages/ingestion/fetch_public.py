import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.pipeline.live_context import fetch_live_context


def fetch_for_company(name: str, firecrawl_key: str | None) -> tuple[str, list[str]]:
    return fetch_live_context(name, firecrawl_key)
