"""GitHub org + repos + commit activity — engineering lane (multi-strategy org resolution)."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from rag.connectors.base import BaseConnector, ConnectorResult, RawChunk, normalize_connector_text
from rag.connectors.http_client import safe_get

logger = logging.getLogger(__name__)

GITHUB_ORG_BLOCKLIST = frozenset(
    {
        "features",
        "pricing",
        "enterprise",
        "topics",
        "sponsors",
        "marketplace",
        "settings",
        "login",
        "signup",
        "security",
        "about",
    }
)


class GitHubConnector(BaseConnector):
    connector_id = "github_connector"
    lane = "engineering"

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "User-Agent": "DealScannr-Connector"}
        tok = (self.settings.github_token or "").strip()
        if tok:
            h["Authorization"] = f"token {tok}"
        else:
            logger.warning("github_connector_no_token_unauthenticated_rate_limit")
        return h

    async def _search_users(self, headers: dict[str, str], q: str) -> list[dict[str, Any]]:
        try:
            sr = await safe_get(
                "https://api.github.com/search/users",
                params={"q": q, "per_page": "8"},
                headers=headers,
                timeout=25.0,
            )
            sr.raise_for_status()
            data = sr.json()
            items = data.get("items") if isinstance(data, dict) else None
            return items if isinstance(items, list) else []
        except Exception as e:
            logger.debug("github_search_users_failed q=%r: %s", q[:80], e)
            return []

    async def _search_repos_domain(self, headers: dict[str, str], domain: str) -> list[str]:
        logins: list[str] = []
        try:
            rr = await safe_get(
                "https://api.github.com/search/repositories",
                params={"q": f"{domain} in:description", "sort": "stars", "per_page": "8"},
                headers=headers,
                timeout=25.0,
            )
            rr.raise_for_status()
            data = rr.json()
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                return []
            for repo in items:
                if not isinstance(repo, dict):
                    continue
                owner = repo.get("owner")
                if isinstance(owner, dict):
                    login = str(owner.get("login") or "")
                    if login and login not in logins:
                        logins.append(login)
        except Exception as e:
            logger.debug("github_search_repos_failed: %s", e)
        return logins

    def _github_logins_from_html(self, html: str) -> list[str]:
        found: list[str] = []
        for m in re.finditer(
            r"github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})",
            html,
            re.I,
        ):
            login = m.group(1)
            if login.lower() in GITHUB_ORG_BLOCKLIST:
                continue
            if login not in found:
                found.append(login)
        return found[:12]

    async def _homepage_github_hints(self, domain: str, headers: dict[str, str]) -> list[str]:
        dom = (domain or "").strip().lower()
        dom = dom.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if dom.startswith("www."):
            dom = dom[4:]
        if not dom:
            return []
        try:
            # Do not send GitHub Authorization to the company origin.
            neutral_headers = {"User-Agent": headers.get("User-Agent", "DealScannr-Connector")}
            r = await safe_get(
                f"https://{dom}/",
                entity_domain=dom,
                headers=neutral_headers,
                timeout=20.0,
                follow_redirects=True,
            )
            if r.status_code >= 400:
                return []
            return self._github_logins_from_html(r.text[:200_000])
        except Exception as e:
            logger.debug("github_homepage_fetch_failed: %s", e)
            return []

    async def _verify_org(self, headers: dict[str, str], login: str) -> bool:
        try:
            org_r = await safe_get(f"https://api.github.com/orgs/{login}", headers=headers, timeout=20.0)
            return org_r.status_code == 200
        except Exception:
            return False

    async def _get_org_dict(self, headers: dict[str, str], login: str) -> dict[str, Any]:
        try:
            org_r = await safe_get(f"https://api.github.com/orgs/{login}", headers=headers, timeout=20.0)
            if org_r.status_code != 200:
                return {}
            data = org_r.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _org_domain_confidence(self, org: dict[str, Any], login: str, dom: str) -> float:
        """Score 0–1: how likely this org is the official company (vs community fork)."""
        blog = str(org.get("blog") or "").strip().lower()
        lg = (login or "").strip().lower()
        d = (dom or "").strip().lower()
        if not d:
            return 0.5
        bare = d[4:] if d.startswith("www.") else d
        blog_n = blog.replace("www.", "")
        suspicious = (
            "-enhancer",
            "-plugin",
            "-unofficial",
            "awesome-",
            "community-",
            "-community",
        )
        if any(s in lg for s in suspicious):
            return 0.32
        # Strong: org blog/homepage references company domain
        if bare and (bare in blog_n or blog_n.rstrip("/").endswith(bare)):
            return 0.95
        root = bare.split(".")[0] if bare else ""
        compact = bare.replace(".", "") if bare else ""
        if compact and lg == compact:
            return 0.9
        if root and lg == root and len(root) >= 3:
            return 0.88
        if root and len(root) >= 4 and root in lg:
            return 0.58 if blog else 0.42
        if root and len(root) >= 3 and root in lg:
            return 0.52 if blog else 0.38
        return 0.35

    async def _ordered_org_candidates(
        self,
        headers: dict[str, str],
        domain: str,
        legal_name: str,
    ) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []

        def add_batch(logins: list[str]) -> None:
            for lg in logins:
                low = lg.lower()
                if low in seen:
                    continue
                seen.add(low)
                ordered.append(lg)

        if domain:
            # Full hostname first (e.g. notion.so type:org → official orgs tied to domain)
            add_batch(
                [
                    str((x or {}).get("login") or "")
                    for x in await self._search_users(headers, f"{domain} type:org")
                    if isinstance(x, dict)
                ]
            )
        ln = (legal_name or "").strip()
        if ln:
            add_batch(
                [
                    str((x or {}).get("login") or "")
                    for x in await self._search_users(headers, f"{ln} type:org")
                    if isinstance(x, dict)
                ]
            )
            nospace = re.sub(r"\s+", "", ln)
            if nospace != ln:
                add_batch(
                    [
                        str((x or {}).get("login") or "")
                        for x in await self._search_users(headers, f"{nospace} type:org")
                        if isinstance(x, dict)
                    ]
                )

        if domain:
            add_batch(await self._search_repos_domain(headers, domain))
            add_batch(await self._homepage_github_hints(domain, headers))

        return [x for x in ordered if x]

    async def _commit_activity_last_4_weeks(
        self,
        headers: dict[str, str],
        login: str,
        repo: str,
    ) -> int | None:
        url = f"https://api.github.com/repos/{login}/{repo}/stats/commit_activity"
        for _attempt in range(4):
            try:
                r = await safe_get(url, headers=headers, timeout=25.0)
                if r.status_code == 202:
                    await asyncio.sleep(1.0)
                    continue
                if r.status_code != 200:
                    return None
                data = r.json()
                if not isinstance(data, list) or len(data) < 4:
                    return None
                last4 = data[-4:]
                total = 0
                for week in last4:
                    if isinstance(week, dict) and isinstance(week.get("total"), int):
                        total += week["total"]
                return total
            except Exception as e:
                logger.debug("github_commit_activity_err %s/%s: %s", login, repo, e)
                return None
        return None

    async def _fetch_impl(
        self,
        entity_id: str,
        scan_id: str,
        legal_name: str,
        domain: str,
    ) -> ConnectorResult:
        retrieved_at = datetime.now(timezone.utc)
        dom = (domain or "").strip().lower()
        dom = dom.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if dom.startswith("www."):
            dom = dom[4:]
        if not dom:
            dom = legal_name.lower().replace(" ", "") + ".com"

        headers = self._headers()
        candidates = await self._ordered_org_candidates(headers, dom, legal_name)
        scored: list[tuple[str, float, dict[str, Any]]] = []
        seen_l: set[str] = set()
        for cand in candidates:
            cl = cand.lower()
            if cl in seen_l:
                continue
            seen_l.add(cl)
            if not await self._verify_org(headers, cand):
                continue
            org_d = await self._get_org_dict(headers, cand)
            if not org_d:
                continue
            conf = self._org_domain_confidence(org_d, cand, dom)
            scored.append((cand, conf, org_d))
        scored.sort(key=lambda x: x[1], reverse=True)

        MIN_ORG_CONF = 0.55
        login = ""
        org: dict[str, Any] = {}
        match_confidence = 0.0
        if scored and scored[0][1] >= MIN_ORG_CONF:
            login, match_confidence, org = scored[0]

        if not login:
            text = (
                f"No public GitHub organization found for {dom}. "
                f"The company may use private repositories or self-hosted Git (e.g. Gitea, GitLab)."
            )
            chunk = RawChunk(
                source_url=f"https://{dom}/"[:2000],
                raw_text=text,
                normalized_text=normalize_connector_text(text),
                retrieved_at=retrieved_at,
                connector_id=self.connector_id,
                entity_id=entity_id,
                scan_id=scan_id,
                metadata={"kind": "no_public_github"},
            )
            return ConnectorResult(
                connector_id=self.connector_id,
                chunks=[chunk],
                status="partial",
                retrieved_at=retrieved_at,
                error="no_github_org_found",
                lane=self.lane,
            )

        try:
            repos_r = await safe_get(
                f"https://api.github.com/orgs/{login}/repos",
                params={"sort": "pushed", "per_page": "10"},
                headers=headers,
                timeout=25.0,
            )
            repos_r.raise_for_status()
            repos = repos_r.json() if isinstance(repos_r.json(), list) else []
        except Exception as e:
            return ConnectorResult(
                connector_id=self.connector_id,
                chunks=[],
                status="failed",
                retrieved_at=retrieved_at,
                error=str(e),
                lane=self.lane,
            )

        repos_sorted = sorted(
            [r for r in repos if isinstance(r, dict)],
            key=lambda x: int(x.get("stargazers_count") or 0),
            reverse=True,
        )[:5]

        chunks: list[RawChunk] = []
        top_name = ""
        if repos_sorted:
            top_name = str(repos_sorted[0].get("full_name") or repos_sorted[0].get("name") or "")

        pct = int(round(max(0.0, min(1.0, match_confidence)) * 100))
        summary_text = (
            f"GitHub org: {login} (match confidence: {pct}%). "
            f"Public repos: {org.get('public_repos', 0)}. "
            f"Followers: {org.get('followers', 0)}. Most active repo: {top_name or 'n/a'}."
        )
        chunks.append(
            RawChunk(
                source_url=str(org.get("html_url") or f"https://github.com/{login}")[:2000],
                raw_text=summary_text,
                normalized_text=normalize_connector_text(summary_text),
                retrieved_at=retrieved_at,
                connector_id=self.connector_id,
                entity_id=entity_id,
                scan_id=scan_id,
                metadata={"kind": "org_summary"},
            )
        )

        repo_chunks = 0
        for r in repos_sorted:
            if repo_chunks >= 9:
                break
            name = str(r.get("name") or "")
            if not name:
                continue
            full = str(r.get("full_name") or f"{login}/{name}")
            commits = await self._commit_activity_last_4_weeks(headers, login, name)
            cpart = f"{commits} commits" if commits is not None else "commits n/a"
            text = (
                f"GitHub repo: {full}. Language: {r.get('language') or 'unknown'}. "
                f"Stars: {r.get('stargazers_count', 0)}. Forks: {r.get('forks_count', 0)}. "
                f"Last pushed: {r.get('pushed_at') or ''}. "
                f"Recent commit activity (last 4 weeks): {cpart}."
            )
            chunks.append(
                RawChunk(
                    source_url=str(r.get("html_url") or "")[:2000],
                    raw_text=text,
                    normalized_text=normalize_connector_text(text),
                    retrieved_at=retrieved_at,
                    connector_id=self.connector_id,
                    entity_id=entity_id,
                    scan_id=scan_id,
                    metadata={"repo": name},
                )
            )
            repo_chunks += 1

        st: str = "complete" if len(chunks) >= 3 else "partial"
        return ConnectorResult(
            connector_id=self.connector_id,
            chunks=chunks[:10],
            status=st,  # type: ignore[arg-type]
            retrieved_at=retrieved_at,
            error=None,
            lane=self.lane,
        )
