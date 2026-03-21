"""Run all connectors in parallel; never raise from this module."""

from __future__ import annotations

import asyncio
import logging

from rag.connectors.base import BaseConnector, ConnectorResult
from rag.connectors.courtlistener import CourtListenerConnector
from rag.connectors.github_connector import GitHubConnector
from rag.connectors.hiring_connector import HiringConnector
from rag.connectors.news_connector import NewsConnector
from rag.connectors.sec_edgar import SecEdgarConnector
from rag.connectors.wikipedia_connector import WikipediaConnector
from rag.connectors.settings import ConnectorSettings

logger = logging.getLogger(__name__)


def lane_coverage_from_results(results: list[ConnectorResult]) -> int:
    """One point per lane with any non-failed connector that returned chunks."""
    lanes: set[str] = set()
    for r in results:
        if r.status != "failed" and r.chunks:
            lanes.add(r.lane)
    return len(lanes)


def build_connectors(settings: ConnectorSettings) -> list[BaseConnector]:
    return [
        SecEdgarConnector(settings),
        CourtListenerConnector(settings),
        GitHubConnector(settings),
        HiringConnector(settings),
        NewsConnector(settings),
        WikipediaConnector(settings),
    ]


async def run_all_connectors(
    entity_id: str,
    scan_id: str,
    legal_name: str,
    domain: str,
    settings: ConnectorSettings,
) -> list[ConnectorResult]:
    connectors = build_connectors(settings)
    tasks = [c.fetch_with_retry(entity_id, scan_id, legal_name, domain) for c in connectors]
    raw = await asyncio.gather(*tasks, return_exceptions=True)
    final: list[ConnectorResult] = []
    for c, result in zip(connectors, raw):
        if isinstance(result, Exception):
            logger.warning("connector_gather_exception %s: %s", c.connector_id, result)
            final.append(c.empty_result(str(result)))
        else:
            final.append(result)
    return final
