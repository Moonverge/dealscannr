"""News baseline: GDELT (free) → DuckDuckGo → Bing News RSS → optional NewsAPI if not 426."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from rag.connectors.base import BaseConnector, ConnectorResult, RawChunk, normalize_connector_text
from rag.connectors.http_client import safe_get
from rag.connectors.web_search_fallback import bing_rss_entries, ddg_search_snippets

logger = logging.getLogger(__name__)

NEWS_API_EVERYTHING = "https://newsapi.org/v2/everything"
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"


class NewsConnector(BaseConnector):
    connector_id = "news_connector"
    lane = "news"

    def _build_gdelt_query(self, legal_name: str) -> str | None:
        """GDELT rejects domain-style queries; use keyword-style text only."""
        name = (legal_name or "").strip()
        if not name:
            return None
        if "." in name:
            name = name.split(".")[0].strip()
        if len(name) < 4:
            return None
        return name

    def _gdelt_query_variants(self, legal_name: str, domain: str) -> list[str]:
        queries = [legal_name]
        d = (domain or "").strip().lower()
        if d.startswith("www."):
            d = d[4:]
        domain_root = d.split(".")[0] if d else ""
        if domain_root and domain_root.lower() != (legal_name or "").strip().lower():
            if len(domain_root) >= 4:
                queries.append(domain_root)
        return queries

    async def _fetch_gdelt(
        self,
        query: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        q = self._build_gdelt_query(query)
        if q is None:
            return []
        logger.info("gdelt_query_built query=%r", q)
        try:
            await asyncio.sleep(2.0)
            r = await safe_get(
                GDELT_DOC,
                params={
                    "query": q,
                    "mode": "ArtList",
                    "maxrecords": "10",
                    "format": "json",
                    "timespan": "30d",
                },
                timeout=28.0,
            )
            r.raise_for_status()
            if not r.text.strip().startswith("{"):
                logger.warning("gdelt_non_json_response prefix=%r", r.text[:120])
                return []
            data = r.json()
        except Exception as e:
            logger.warning("gdelt_failed: %s", e)
            return []
        if not isinstance(data, dict):
            return []
        arts = data.get("articles")
        if not isinstance(arts, list):
            return []
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        for a in arts[:10]:
            if not isinstance(a, dict):
                continue
            lang = str(a.get("language") or "").lower()
            if lang and lang != "english":
                continue
            title = str(a.get("title") or "")
            url = str(a.get("url") or "")
            dom = str(a.get("domain") or "")
            seen = str(a.get("seendate") or "")
            if not title and not url:
                continue
            text = f"News: {title}. Source: {dom}. Date: {seen}. URL: {url}"
            if len(normalize_connector_text(text)) < 20:
                continue
            out.append(
                RawChunk(
                    source_url=(url or GDELT_DOC)[:2000],
                    raw_text=text,
                    normalized_text=normalize_connector_text(text),
                    retrieved_at=retrieved_at,
                    connector_id=self.connector_id,
                    entity_id=entity_id,
                    scan_id=scan_id,
                    metadata={"source": "gdelt"},
                )
            )
        return out

    def _news_query(self, legal_name: str, domain: str) -> str:
        d = (domain or "").strip().lower().split("/")[0].replace("https://", "").replace("http://", "")
        if d.startswith("www."):
            d = d[4:]
        return f"{legal_name} {d}".strip() if d else legal_name

    async def _chunks_from_ddg(self, legal_name: str, domain: str, entity_id: str, scan_id: str) -> list[RawChunk]:
        q = self._news_query(legal_name, domain)
        snippets = await ddg_search_snippets(f"{q} news", max_results=8)
        if not snippets:
            return []
        retrieved_at = datetime.now(timezone.utc)
        blob = "\n---\n".join(snippets)[:6000]
        text = f"News (DuckDuckGo aggregate): {blob[:2000]}"
        return [
            RawChunk(
                source_url="https://api.duckduckgo.com/",
                raw_text=text,
                normalized_text=normalize_connector_text(text),
                retrieved_at=retrieved_at,
                connector_id=self.connector_id,
                entity_id=entity_id,
                scan_id=scan_id,
                metadata={"source": "ddg"},
            )
        ]

    async def _chunks_from_bing_rss(
        self,
        legal_name: str,
        domain: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        seen_urls: set[str] = set()
        variants = self._gdelt_query_variants(legal_name, domain)
        search_strings: list[str] = []
        for v in variants:
            s = self._news_query(v, domain)
            if s and s not in search_strings:
                search_strings.append(s)
        if not search_strings:
            search_strings = [self._news_query(legal_name, domain)]
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        for q in search_strings:
            entries = await bing_rss_entries(f"{q} news", max_results=8)
            for e in entries:
                title = e.get("title") or ""
                link = e.get("link") or "https://www.bing.com/news/"
                desc = (e.get("description") or "")[:400]
                pub = e.get("published") or ""
                text = f"News: {title}. Published: {pub}. {desc} URL: {link}"
                if len(normalize_connector_text(text)) < 20:
                    continue
                u = link[:2000]
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                out.append(
                    RawChunk(
                        source_url=u,
                        raw_text=text,
                        normalized_text=normalize_connector_text(text),
                        retrieved_at=retrieved_at,
                        connector_id=self.connector_id,
                        entity_id=entity_id,
                        scan_id=scan_id,
                        metadata={"source": "bing_rss"},
                    )
                )
                if len(out) >= 8:
                    return out
        return out[:8]

    async def _newsapi_supplement(
        self,
        legal_name: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        key = (self.settings.newsapi_key or "").strip()
        if not key:
            return []
        from_day = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        try:
            r = await safe_get(
                NEWS_API_EVERYTHING,
                params={
                    "q": legal_name,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "from": from_day,
                    "apiKey": key,
                },
                timeout=25.0,
            )
            if r.status_code == 426:
                logger.warning("newsapi_upgrade_required_free_tier_blocks_everything_endpoint")
                return []
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("newsapi_failed: %s", e)
            return []
        arts = data.get("articles") if isinstance(data, dict) else None
        if not isinstance(arts, list):
            return []
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        for a in arts[:10]:
            if not isinstance(a, dict):
                continue
            title = str(a.get("title") or "")
            desc = str(a.get("description") or a.get("content") or "")[:300]
            pub = str(a.get("publishedAt") or "")
            src = a.get("source") if isinstance(a.get("source"), dict) else {}
            sname = str((src or {}).get("name") or "news")
            url = str(a.get("url") or "https://newsapi.org")
            text = f"News: {title}. Source: {sname}. Published: {pub}. Summary: {desc}"
            if len(normalize_connector_text(text)) < 20:
                continue
            out.append(
                RawChunk(
                    source_url=url[:2000],
                    raw_text=text,
                    normalized_text=normalize_connector_text(text),
                    retrieved_at=retrieved_at,
                    connector_id=self.connector_id,
                    entity_id=entity_id,
                    scan_id=scan_id,
                    metadata={"source": "newsapi"},
                )
            )
        return out

    async def _fetch_impl(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        retrieved_at = datetime.now(timezone.utc)
        chunks: list[RawChunk] = []
        seen_urls: set[str] = set()

        def _append_deduped(new: list[RawChunk]) -> None:
            for c in new:
                if c.source_url not in seen_urls:
                    seen_urls.add(c.source_url)
                    chunks.append(c)

        gdelt_queries = self._gdelt_query_variants(legal_name, domain)
        for query in gdelt_queries:
            try:
                _append_deduped(await self._fetch_gdelt(query, entity_id, scan_id))
            except Exception as e:
                logger.warning("gdelt_failed_unexpected: %s", e)

        if len(chunks) < 3:
            try:
                _append_deduped(await self._chunks_from_ddg(legal_name, domain, entity_id, scan_id))
            except Exception as e:
                logger.warning("ddg_news_failed: %s", e)

        if len(chunks) < 5:
            try:
                _append_deduped(
                    await self._chunks_from_bing_rss(legal_name, domain, entity_id, scan_id)
                )
            except Exception as e:
                logger.warning("bing_rss_news_failed: %s", e)

        if len(chunks) < 8:
            _append_deduped(await self._newsapi_supplement(legal_name, entity_id, scan_id))

        chunks = chunks[:10]

        if len(chunks) >= 3:
            st = "complete"
        elif len(chunks) > 0:
            st = "partial"
        else:
            st = "failed"

        return ConnectorResult(
            connector_id=self.connector_id,
            chunks=chunks,
            status=st,  # type: ignore[arg-type]
            retrieved_at=retrieved_at,
            error=None if chunks else "no_news",
            lane=self.lane,
        )
