"""Shared DuckDuckGo instant-answer + Bing News RSS helpers for connectors."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser

from rag.connectors.http_client import safe_get

logger = logging.getLogger(__name__)

DDG_API = "https://api.duckduckgo.com/"


async def ddg_search_snippets(query: str, max_results: int = 8) -> list[str]:
    """Return short text snippets from DuckDuckGo Instant Answer API (no HTML)."""
    try:
        r = await safe_get(
            DDG_API,
            params={
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            },
            timeout=10.0,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("ddg_search_failed query=%r err=%s", query[:80], e)
        return []
    out: list[str] = []
    ab = (data.get("AbstractText") or data.get("Abstract") or "").strip()
    if ab:
        out.append(ab)
    for t in (data.get("RelatedTopics") or [])[: max_results * 2]:
        if isinstance(t, dict) and (t.get("Text") or ""):
            out.append(str(t["Text"]))
        elif isinstance(t, list):
            for sub in t:
                if isinstance(sub, dict) and sub.get("Text"):
                    out.append(str(sub["Text"]))
        if len(out) >= max_results:
            break
    return out[:max_results]


async def bing_rss_entries(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Parse Bing News RSS into {title, link, description, published}."""
    url = f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss"
    try:
        r = await safe_get(url, timeout=10.0, follow_redirects=True)
        r.raise_for_status()
        feed = feedparser.parse(r.text)
    except Exception as e:
        logger.warning("bing_rss_failed query=%r err=%s", query[:80], e)
        return []
    rows: list[dict[str, str]] = []
    for e in getattr(feed, "entries", [])[:max_results]:
        rows.append(
            {
                "title": getattr(e, "title", "") or "",
                "link": getattr(e, "link", "") or "",
                "description": getattr(e, "summary", "") or "",
                "published": getattr(e, "published", "") or "",
            }
        )
    return rows
