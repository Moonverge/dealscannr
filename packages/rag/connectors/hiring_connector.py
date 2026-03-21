"""Hiring signals: Remotive → optional Adzuna → DuckDuckGo → entity careers pages."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from rapidfuzz import fuzz

from rag.connectors.base import BaseConnector, ConnectorResult, RawChunk, normalize_connector_text
from rag.connectors.http_client import safe_get
from rag.connectors.web_search_fallback import ddg_search_snippets

logger = logging.getLogger(__name__)

REMOTIVE_JOBS = "https://remotive.com/api/remote-jobs"


def _html_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]{2,400})", html, re.I | re.DOTALL)
    if not m:
        return ""
    return normalize_connector_text(re.sub(r"\s+", " ", m.group(1)))


def _strip_tags(html: str, max_len: int = 3500) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = normalize_connector_text(t)
    return t[:max_len]


class HiringConnector(BaseConnector):
    connector_id = "hiring_connector"
    lane = "hiring"

    def _job_company_passes_filter(self, job_company: str, legal_name: str) -> bool:
        jc = (job_company or "").strip().lower()
        ln = (legal_name or "").strip().lower()
        if not jc or not ln:
            return False
        if ln in jc or jc in ln:
            return True
        score = fuzz.partial_ratio(ln, jc)
        if score < 60:
            return False
        if ln not in jc and jc not in ln:
            words = [w for w in ln.split() if len(w) > 2]
            if words and not any(w in jc for w in words):
                return False
        return True

    async def _remotive_chunks(
        self,
        legal_name: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        try:
            r = await safe_get(
                REMOTIVE_JOBS,
                params={"search": legal_name, "limit": "50"},
                timeout=28.0,
                headers={"User-Agent": "DealScannr-Connector/1.0 (+https://dealscannr.com)"},
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("remotive_failed: %s", e)
            return []
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            return []
        for job in jobs[:40]:
            if not isinstance(job, dict):
                continue
            company = str(job.get("company_name") or "")
            if not self._job_company_passes_filter(company, legal_name):
                continue
            title = str(job.get("title") or "")
            url = str(job.get("url") or REMOTIVE_JOBS)
            loc = str(job.get("candidate_required_location") or job.get("job_type") or "")
            posted = str(job.get("publication_date") or "")
            text = f"Job: {title} at {company}, {loc}. Posted: {posted}. URL: {url}"
            if len(normalize_connector_text(text)) < 15:
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
                    metadata={"source": "remotive"},
                )
            )
            if len(out) >= 10:
                break
        return out

    async def _adzuna_chunks(
        self,
        legal_name: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        app_id = (self.settings.adzuna_app_id or "").strip()
        app_key = (self.settings.adzuna_api_key or "").strip()
        if not app_id or not app_key:
            return []
        country = (self.settings.adzuna_country or "us").strip().lower() or "us"
        retrieved_at = datetime.now(timezone.utc)
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        try:
            r = await safe_get(
                url,
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": legal_name,
                    "results_per_page": "10",
                },
                timeout=25.0,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("adzuna_failed: %s", e)
            return []
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            return []
        out: list[RawChunk] = []
        for row in results[:10]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "")
            comp = str((row.get("company") or {}).get("display_name") or "")
            if not self._job_company_passes_filter(comp, legal_name):
                continue
            locs = row.get("location") or {}
            loc = ""
            if isinstance(locs, dict):
                loc = str(locs.get("display_name") or locs.get("area") or "")
            created = str(row.get("created") or "")
            redir = str(row.get("redirect_url") or "https://api.adzuna.com/")
            text = f"Job: {title} at {comp}, {loc}. Posted: {created}. URL: {redir}"
            if len(normalize_connector_text(text)) < 15:
                continue
            out.append(
                RawChunk(
                    source_url=redir[:2000],
                    raw_text=text,
                    normalized_text=normalize_connector_text(text),
                    retrieved_at=retrieved_at,
                    connector_id=self.connector_id,
                    entity_id=entity_id,
                    scan_id=scan_id,
                    metadata={"source": "adzuna"},
                )
            )
        return out

    async def _ddg_job_chunks(self, legal_name: str, entity_id: str, scan_id: str) -> list[RawChunk]:
        snippets = await ddg_search_snippets(f"{legal_name} jobs hiring careers", max_results=6)
        if not snippets:
            return []
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        for snip in snippets[:5]:
            if len(normalize_connector_text(snip)) < 25:
                continue
            text = f"Hiring signal (web aggregate): {snip}"
            out.append(
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
            )
        return out

    async def _careers_page_chunks(
        self,
        legal_name: str,
        domain: str,
        entity_id: str,
        scan_id: str,
    ) -> list[RawChunk]:
        dom = (domain or "").strip().lower()
        dom = dom.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if not dom:
            return []
        if dom.startswith("www."):
            dom = dom[4:]
        urls = [
            f"https://{dom}/careers",
            f"https://{dom}/jobs",
            f"https://careers.{dom}/",
        ]
        retrieved_at = datetime.now(timezone.utc)
        out: list[RawChunk] = []
        for u in urls:
            try:
                r = await safe_get(
                    u,
                    entity_domain=dom,
                    timeout=18.0,
                    follow_redirects=True,
                    headers={"User-Agent": "DealScannr-Connector/1.0"},
                )
                if r.status_code >= 400:
                    continue
                html = r.text[:120_000]
                title = _html_title(html)
                body = _strip_tags(html, 2800)
                if len(body) < 80 and len(title) < 10:
                    continue
                text = (
                    f"Careers page ({u}): title {title}. "
                    f"Extracted text preview: {body[:1200]}"
                )
                out.append(
                    RawChunk(
                        source_url=u[:2000],
                        raw_text=text,
                        normalized_text=normalize_connector_text(text),
                        retrieved_at=retrieved_at,
                        connector_id=self.connector_id,
                        entity_id=entity_id,
                        scan_id=scan_id,
                        metadata={"source": "careers_page"},
                    )
                )
                if len(out) >= 3:
                    break
            except Exception as e:
                logger.debug("careers_page_skip %s: %s", u, e)
        return out

    async def _fetch_impl(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        retrieved_at = datetime.now(timezone.utc)
        detail_chunks: list[RawChunk] = []
        sources_used: list[str] = []

        rem = await self._remotive_chunks(legal_name, entity_id, scan_id)
        if rem:
            sources_used.append("remotive")
        detail_chunks.extend(rem)

        adz = await self._adzuna_chunks(legal_name, entity_id, scan_id)
        if adz:
            sources_used.append("adzuna")
        detail_chunks.extend(adz)

        ddg = await self._ddg_job_chunks(legal_name, entity_id, scan_id)
        if ddg:
            sources_used.append("ddg")
        detail_chunks.extend(ddg)

        careers = await self._careers_page_chunks(legal_name, domain, entity_id, scan_id)
        if careers:
            sources_used.append("careers_site")
        detail_chunks.extend(careers)

        job_rows = [c for c in detail_chunks if "Job:" in (c.raw_text or "")]
        titles: list[str] = []
        for ch in job_rows:
            m = re.search(r"Job:\s*([^.|]+)", ch.normalized_text, re.I)
            if m:
                titles.append(normalize_connector_text(m.group(1))[:80])
        top_titles = ", ".join(titles[:5]) or "none extracted"
        n_verified = len(job_rows)

        if n_verified == 0:
            summary = (
                f"No verified open roles found for {legal_name} on Remotive or Adzuna "
                f"(company name did not match job postings). The company may list roles only on its own careers page."
            )
        else:
            summary = (
                f"Hiring summary: {n_verified} verified open role(s) at {legal_name} "
                f"across {', '.join(sources_used) or 'sources'}. Roles: {top_titles}."
            )
        summary_chunk = RawChunk(
            source_url="https://remotive.com/api/remote-jobs",
            raw_text=summary,
            normalized_text=normalize_connector_text(summary),
            retrieved_at=retrieved_at,
            connector_id=self.connector_id,
            entity_id=entity_id,
            scan_id=scan_id,
            metadata={"kind": "summary"},
        )

        all_chunks = [summary_chunk] + [c for c in detail_chunks if c.metadata.get("kind") != "summary"]
        all_chunks = all_chunks[:16]

        # Must not use status "failed" when we have a summary chunk: fetch_with_retry would drop chunks.
        detail_only = len([c for c in all_chunks if c.metadata.get("kind") != "summary"])
        if detail_only == 0:
            st: str = "partial"
            err = "no_hiring_signal"
        elif len(all_chunks) >= 5:
            st = "complete"
            err = None
        else:
            st = "partial"
            err = None

        return ConnectorResult(
            connector_id=self.connector_id,
            chunks=all_chunks,
            status=st,  # type: ignore[arg-type]
            retrieved_at=retrieved_at,
            error=err,
            lane=self.lane,
        )
