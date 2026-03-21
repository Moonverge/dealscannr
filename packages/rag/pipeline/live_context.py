from __future__ import annotations

import json
import re
from typing import Any

from rag.connectors.http_client import safe_get_sync, safe_post_sync

FIRECRAWL_SEARCH = "https://api.firecrawl.dev/v2/search"
FIRECRAWL_SCRAPE = "https://api.firecrawl.dev/v2/scrape"

_HAS_SCHEME = re.compile(r"^https?://", re.I)
# Single token that looks like a hostname + optional path (e.g. kooya.ph, www.x.com/about)
_DOMAIN_LIKE = re.compile(
    r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(/[^\s]*)?$",
    re.I,
)


def normalize_url_candidate(text: str) -> str | None:
    """If the query is clearly a URL or bare domain, return a fetchable https URL."""
    s = (text or "").strip()
    if not s or " " in s:
        return None
    if _HAS_SCHEME.match(s):
        return s
    if _DOMAIN_LIKE.fullmatch(s):
        return f"https://{s}"
    return None


def _firecrawl_scrape_url(url: str, api_key: str) -> tuple[str, list[str]]:
    body: dict[str, Any] = {
        "url": url,
        "formats": [{"type": "markdown"}],
    }
    try:
        r = safe_post_sync(
            FIRECRAWL_SCRAPE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=90.0,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return "", []
    if not payload.get("success"):
        return "", []
    data = payload.get("data") or {}
    md = (data.get("markdown") or "").strip()
    if not md:
        return "", []
    block = f"DIRECT PAGE SCRAPE\nURL: {url}\n\n{md[:12000]}"
    return block, [url]


def _firecrawl(company_name: str, api_key: str) -> tuple[str, list[str]]:
    body: dict[str, Any] = {
        "query": f"{company_name} company startup funding",
        "limit": 5,
        "sources": [{"type": "web"}],
        "scrapeOptions": {"formats": [{"type": "markdown"}]},
    }
    try:
        r = safe_post_sync(
            FIRECRAWL_SEARCH,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60.0,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return "", []
    if not payload.get("success"):
        return "", []
    data = payload.get("data") or {}
    web = data.get("web") or []
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


def _duckduckgo(company_name: str) -> tuple[str, list[str]]:
    urls: list[str] = []
    parts: list[str] = []
    try:
        r = safe_get_sync(
            "https://api.duckduckgo.com/",
            params={
                "q": company_name,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
            timeout=20.0,
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


def fetch_live_context(
    company_name: str,
    firecrawl_api_key: str | None,
) -> tuple[str, list[str]]:
    if firecrawl_api_key:
        direct = normalize_url_candidate(company_name)
        if direct:
            text, urls = _firecrawl_scrape_url(direct, firecrawl_api_key)
            if text:
                return text, urls
        text, urls = _firecrawl(company_name, firecrawl_api_key)
        if text:
            return text, urls
    return _duckduckgo(company_name)
