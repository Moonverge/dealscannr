"""Live web context fallback: async Firecrawl (scrape+search concurrent) → DuckDuckGo."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from rag.connectors.http_client import safe_get, safe_post

logger = logging.getLogger(__name__)

FIRECRAWL_SEARCH = "https://api.firecrawl.dev/v2/search"
FIRECRAWL_SCRAPE = "https://api.firecrawl.dev/v2/scrape"

_HAS_SCHEME = re.compile(r"^https?://", re.I)
_DOMAIN_LIKE = re.compile(
    r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(/[^\s]*)?$", re.I,
)


def normalize_url_candidate(text: str) -> str | None:
    s = (text or "").strip()
    if not s or " " in s:
        return None
    if _HAS_SCHEME.match(s):
        return s
    if _DOMAIN_LIKE.fullmatch(s):
        return f"https://{s}"
    return None


# ── async implementations ──────────────────────────────────────────────


async def _firecrawl_scrape_async(url: str, api_key: str) -> tuple[str, list[str]]:
    try:
        r = await safe_post(
            FIRECRAWL_SCRAPE,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"url": url, "formats": [{"type": "markdown"}]},
            timeout=45.0,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return "", []
    if not payload.get("success"):
        return "", []
    md = ((payload.get("data") or {}).get("markdown") or "").strip()
    if not md:
        return "", []
    return f"DIRECT PAGE SCRAPE\nURL: {url}\n\n{md[:12000]}", [url]


async def _firecrawl_search_async(company_name: str, api_key: str) -> tuple[str, list[str]]:
    body: dict[str, Any] = {
        "query": f"{company_name} company startup funding",
        "limit": 5,
        "sources": [{"type": "web"}],
        "scrapeOptions": {"formats": [{"type": "markdown"}]},
    }
    try:
        r = await safe_post(
            FIRECRAWL_SEARCH,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=30.0,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return "", []
    if not payload.get("success"):
        return "", []
    web = (payload.get("data") or {}).get("web") or []
    parts: list[str] = []
    urls: list[str] = []
    for item in web[:8]:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        desc = (item.get("description") or "").strip()
        md = (item.get("markdown") or "").strip()
        if url:
            urls.append(url)
        block = f"URL: {url}\nTitle: {title}\nSnippet: {desc}\n"
        if md:
            block += f"Content:\n{md[:4000]}\n"
        parts.append(block)
    return "\n---\n".join(parts).strip(), urls


async def _duckduckgo_async(company_name: str) -> tuple[str, list[str]]:
    urls: list[str] = []
    parts: list[str] = []
    try:
        r = await safe_get(
            "https://api.duckduckgo.com/",
            params={"q": company_name, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=12.0,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return "", []
    abstract = (data.get("Abstract") or "").strip()
    abs_url = (data.get("AbstractURL") or "").strip()
    if abs_url:
        urls.append(abs_url)
    if abstract:
        parts.append(f"Abstract ({abs_url or 'DDG'}):\n{abstract}")
    for topic in (data.get("RelatedTopics") or [])[:6]:
        if isinstance(topic, dict):
            t = (topic.get("Text") or "").strip()
            u = (topic.get("FirstURL") or "").strip()
            if u and u not in urls:
                urls.append(u)
            if t:
                parts.append(f"{t}\n{u}")
        elif isinstance(topic, list):
            for sub in topic[:3]:
                if isinstance(sub, dict):
                    t = (sub.get("Text") or "").strip()
                    u = (sub.get("FirstURL") or "").strip()
                    if u and u not in urls:
                        urls.append(u)
                    if t:
                        parts.append(f"{t}\n{u}")
    infobox = data.get("Infobox") or {}
    if isinstance(infobox, dict) and infobox.get("content"):
        try:
            parts.append("Infobox:\n" + json.dumps(infobox.get("content"), indent=0)[:2000])
        except Exception:
            pass
    return "\n---\n".join(parts).strip(), urls


async def _fetch_live_context_async(
    company_name: str,
    firecrawl_api_key: str | None,
) -> tuple[str, list[str]]:
    if firecrawl_api_key:
        direct = normalize_url_candidate(company_name)
        if direct:
            results = await asyncio.gather(
                _firecrawl_scrape_async(direct, firecrawl_api_key),
                _firecrawl_search_async(company_name, firecrawl_api_key),
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, tuple) and res[0]:
                    return res
        else:
            text, urls = await _firecrawl_search_async(company_name, firecrawl_api_key)
            if text:
                return text, urls
    return await _duckduckgo_async(company_name)


# ── sync wrapper (safe from any event-loop context) ────────────────────


def fetch_live_context(
    company_name: str,
    firecrawl_api_key: str | None,
) -> tuple[str, list[str]]:
    """Sync entry point: runs async pipeline in a dedicated thread."""
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(
            asyncio.run,
            _fetch_live_context_async(company_name, firecrawl_api_key),
        )
        try:
            return future.result(timeout=50)
        except Exception as e:
            logger.warning("live_context_failed: %s", e)
            return "", []
