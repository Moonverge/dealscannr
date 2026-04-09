from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from rag.connectors.settings import ConnectorSettings


def normalize_connector_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


@dataclass
class RawChunk:
    source_url: str
    raw_text: str
    normalized_text: str
    retrieved_at: datetime
    connector_id: str
    entity_id: str
    scan_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ConnectorResult:
    connector_id: str
    chunks: list[RawChunk]
    status: Literal["complete", "partial", "failed"]
    retrieved_at: datetime
    error: str | None = None
    lane: str = ""


class BaseConnector(ABC):
    connector_id: str
    lane: str
    timeout_seconds: int = 15

    def __init__(self, settings: ConnectorSettings | None = None):
        self.settings = settings or ConnectorSettings()

    @abstractmethod
    async def _fetch_impl(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        ...

    async def _fetch_once(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        try:
            return await asyncio.wait_for(
                self._fetch_impl(entity_id, scan_id, legal_name, domain),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return self.empty_result("timeout")
        except Exception as e:
            return self.empty_result(str(e))

    async def fetch(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        return await self._fetch_once(entity_id, scan_id, legal_name, domain)

    async def fetch_with_retry(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
        *,
        max_retries: int = 1,
    ) -> ConnectorResult:
        last_error: str | None = None
        for attempt in range(max_retries + 1):
            result = await self._fetch_once(entity_id, scan_id, legal_name, domain)
            if result.status in ("complete", "partial"):
                return result
            last_error = result.error or "failed"
            if attempt < max_retries:
                await asyncio.sleep(1)
        return self.empty_result(f"source_unavailable:{last_error}")

    def empty_result(self, error: str) -> ConnectorResult:
        return ConnectorResult(
            connector_id=self.connector_id,
            chunks=[],
            status="failed",
            retrieved_at=datetime.now(timezone.utc),
            error=error,
            lane=self.lane,
        )
