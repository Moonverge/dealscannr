"""CourtListener opinion search — litigation lane."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from rapidfuzz import fuzz

from rag.connectors.base import BaseConnector, ConnectorResult, RawChunk, normalize_connector_text
from rag.connectors.http_client import safe_get

logger = logging.getLogger(__name__)

CL_SEARCH_V4 = "https://www.courtlistener.com/api/rest/v4/search/"
CL_SEARCH_V3 = "https://www.courtlistener.com/api/rest/v3/search/"


def _normalize_domain_host(domain: str) -> str:
    d = (domain or "").strip()
    if not d:
        return ""
    if "://" not in d:
        return d.lower().split("/")[0].split(":")[0]
    return (urlparse(d).hostname or "").strip().lower()


def _is_versus_continuation(after: str) -> bool:
    a = after.strip().lower()
    if not a:
        return True
    return (
        a.startswith("v.")
        or a.startswith("vs.")
        or a.startswith("v ")
        or a.startswith("vs ")
        or a.startswith("versus")
    )


def _row_dedupe_key(row: dict) -> str:
    for k in ("id", "cluster_id", "cluster", "absolute_url"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return str(id(row))


def case_matches_entity(case_name: str, legal_name: str, domain: str) -> bool:
    """True only if the case caption plausibly names the target company (not a longer homonym)."""
    name_lower = (legal_name or "").strip().lower()
    if len(name_lower) < 2:
        return False
    case_lower = str(case_name).lower()
    if not case_lower.strip():
        return False

    escaped = re.escape(name_lower)
    pattern = re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")
    for m in pattern.finditer(case_lower):
        after = case_lower[m.end() :].strip()
        if not after:
            return True
        if _is_versus_continuation(after):
            return True
        if not after[0].isalpha():
            return True
        return False

    if name_lower in case_lower:
        idx = case_lower.find(name_lower)
        before_ok = idx == 0 or not case_lower[idx - 1].isalnum()
        end = idx + len(name_lower)
        after_ok = end >= len(case_lower) or not case_lower[end].isalnum()
        if before_ok and after_ok:
            after = case_lower[end:].strip()
            if not after or _is_versus_continuation(after) or not after[0].isalpha():
                return True
            return False

    head = case_lower[:120]
    if fuzz.token_sort_ratio(name_lower, head) > 82:
        return True
    return fuzz.partial_ratio(name_lower, head) >= 88


class CourtListenerConnector(BaseConnector):
    connector_id = "courtlistener"
    lane = "litigation"

    def _search_queries(self, legal_name: str, domain: str) -> list[str]:
        host = _normalize_domain_host(domain)
        queries: list[str] = []
        if host:
            queries.append(f'"{legal_name}" site:{host}')
        queries.append(legal_name)
        return queries

    async def _fetch_impl(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        retrieved_at = datetime.now(timezone.utc)
        key = (self.settings.courtlistener_api_key or "").strip()
        if not key:
            return ConnectorResult(
                connector_id=self.connector_id,
                chunks=[],
                status="failed",
                retrieved_at=retrieved_at,
                error="no api key",
                lane=self.lane,
            )

        headers = {"Authorization": f"Token {key}", "Accept": "application/json"}
        seen: set[str] = set()
        results: list[dict] = []
        for q in self._search_queries(legal_name, domain):
            params = {"q": q, "type": "o", "order_by": "score desc"}
            got: list[dict] = []
            for base in (CL_SEARCH_V4, CL_SEARCH_V3):
                try:
                    r = await safe_get(base, params=params, headers=headers, timeout=25.0)
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    data = r.json()
                    raw = data.get("results")
                    if isinstance(raw, list):
                        got = raw
                        break
                except Exception as e:
                    logger.warning("courtlistener_search_failed base=%s err=%s", base, e)
                    continue
            for row in got:
                if not isinstance(row, dict):
                    continue
                k = _row_dedupe_key(row)
                if k in seen:
                    continue
                seen.add(k)
                results.append(row)

        if not results:
            return ConnectorResult(
                connector_id=self.connector_id,
                chunks=[],
                status="failed",
                retrieved_at=retrieved_at,
                error="no_results",
                lane=self.lane,
            )

        chunks: list[RawChunk] = []
        for row in results[:25]:
            if not isinstance(row, dict):
                continue
            case = row.get("caseName") or row.get("case_name") or ""
            if not case_matches_entity(str(case), legal_name, domain):
                logger.info(
                    "courtlistener_entity_mismatch case=%r legal_name=%r domain=%r",
                    case,
                    legal_name,
                    domain,
                )
                continue
            filed = row.get("dateFiled") or row.get("date_filed") or ""
            court = row.get("court") or ""
            if isinstance(court, dict):
                court = court.get("full_name") or court.get("id") or ""
            status = row.get("status") or ""
            nature = row.get("suitNature") or row.get("nature_of_suit") or ""
            text = (
                f"Court case: {case} filed {filed} in {court}. "
                f"Status: {status}. Nature: {nature}."
            )
            if len(normalize_connector_text(text)) < 15:
                continue
            url = row.get("absolute_url") or row.get("cluster_uri") or "https://www.courtlistener.com"
            if isinstance(url, str) and not url.startswith("http"):
                url = f"https://www.courtlistener.com{url}"
            chunks.append(
                RawChunk(
                    source_url=str(url)[:2000],
                    raw_text=text,
                    normalized_text=normalize_connector_text(text),
                    retrieved_at=retrieved_at,
                    connector_id=self.connector_id,
                    entity_id=entity_id,
                    scan_id=scan_id,
                    metadata={},
                )
            )
            if len(chunks) >= 10:
                break

        st: str = "complete" if len(chunks) >= 3 else "partial"
        if not chunks:
            st = "failed"
        return ConnectorResult(
            connector_id=self.connector_id,
            chunks=chunks,
            status=st,  # type: ignore[arg-type]
            retrieved_at=retrieved_at,
            error=None,
            lane=self.lane,
        )
