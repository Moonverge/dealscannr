"""Compare two completed scans: chunk URLs by lane + Groq notable-change bullets."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from config.settings import settings
from db.mongo import get_database
from modules.api_errors import raise_api_error
from modules.scans.lanes import LANE_CONNECTORS
from rag.engine import RAGEngine
from rag.prompts.grounding_contract import UNIVERSAL_LLM_RULES
from rag.schema.llm_report import ReportOutput

logger = logging.getLogger(__name__)

_REPORT_CORE_KEYS = (
    "verdict",
    "confidence_score",
    "lane_coverage",
    "chunk_count",
    "risk_triage",
    "probe_questions",
    "sections",
    "known_unknowns",
    "disclaimer",
)


def _connector_lane(connector_id: str) -> str | None:
    for lane, names in LANE_CONNECTORS.items():
        if connector_id in names:
            return lane
    return None


async def _urls_by_lane(db: Any, scan_id: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {lane: set() for lane in LANE_CONNECTORS}
    cursor = db.chunks.find({"scan_id": scan_id})
    async for ch in cursor:
        lane = _connector_lane(str(ch.get("connector_id") or ""))
        if not lane:
            continue
        u = str(ch.get("source_url") or "").strip()
        if u:
            out[lane].add(u)
    return out


def _executive_summary(rep: dict[str, Any]) -> str:
    sec = (rep.get("sections") or {}).get("executive_summary") or {}
    return str(sec.get("text") or "")[:8000]


def _parse_bullets(text: str) -> list[str]:
    lines = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith(("-", "*", "•")):
            s = re.sub(r"^[-*•]\s*", "", s).strip()
            if s:
                lines.append(s)
        elif s and len(lines) == 0 and not s.startswith("#"):
            # first non-empty line without marker
            pass
    if not lines and (text or "").strip():
        one = (text or "").strip().split("\n")[0].strip()
        if one:
            lines.append(one[:500])
    return lines[:8]


async def notable_changes_groq(
    old_summary: str,
    new_summary: str,
    new_urls_by_lane: dict[str, list[str]],
) -> list[str]:
    parts = []
    for lane in ("litigation", "engineering", "hiring", "news"):
        urls = new_urls_by_lane.get(lane) or []
        if urls:
            parts.append(f"{lane}: " + ", ".join(urls[:12]))
    signals_txt = "\n".join(parts) if parts else "(none)"

    system = (
        f"{UNIVERSAL_LLM_RULES}\n\n"
        "You compare two diligence report snapshots. Use only the summaries and URL lists "
        "provided in the user message. This is summarization, not factual investigation.\n"
        "Output 3–5 lines. Each line must start with '- ' (bullet). "
        'If there is no meaningful change, output exactly: - No significant changes detected.'
    )
    user = (
        f"Previous report summary:\n{old_summary}\n\n"
        f"Current report summary:\n{new_summary}\n\n"
        f"New source URLs (only in the newer scan, by lane):\n{signals_txt}\n"
    )
    engine = RAGEngine(
        groq_api_key=settings.groq_api_key,
        openai_api_key=settings.openai_api_key,
        llm_provider=settings.llm_provider,
    )
    text, _ = engine._complete(system, user)
    if not (text or "").strip():
        return ["No significant changes detected."]
    bullets = _parse_bullets(text)
    return bullets if bullets else ["No significant changes detected."]


def _as_oid(scan_id: str) -> ObjectId:
    try:
        return ObjectId(scan_id)
    except InvalidId:
        raise_api_error(
            status_code=404,
            error="scan_not_found",
            message="Invalid scan id",
        )


async def compute_scan_diff(
    *,
    user_id: ObjectId,
    new_scan_id: str,
    previous_scan_id: str,
) -> dict[str, Any]:
    db = get_database()
    new_oid = _as_oid(new_scan_id)
    old_oid = _as_oid(previous_scan_id)

    new_scan = await db.scans.find_one({"_id": new_oid})
    old_scan = await db.scans.find_one({"_id": old_oid})
    if not new_scan or not old_scan:
        raise_api_error(status_code=404, error="scan_not_found", message="Scan not found")
    if new_scan.get("user_id") != user_id or old_scan.get("user_id") != user_id:
        raise_api_error(status_code=403, error="forbidden", message="Not allowed to access this scan")
    e_new = str(new_scan.get("entity_id") or "")
    e_old = str(old_scan.get("entity_id") or "")
    if not e_new or e_new != e_old:
        raise_api_error(
            status_code=400,
            error="diff_entity_mismatch",
            message="Scans must belong to the same entity",
        )

    t_new = new_scan.get("created_at")
    t_old = old_scan.get("created_at")
    if isinstance(t_new, datetime) and isinstance(t_old, datetime) and t_new <= t_old:
        raise_api_error(
            status_code=400,
            error="diff_order",
            message="Path scan_id must be newer than compare_to",
        )

    new_rep = await db.reports.find_one({"scan_id": new_scan_id})
    old_rep = await db.reports.find_one({"scan_id": previous_scan_id})
    if not new_rep or not old_rep:
        raise_api_error(
            status_code=400,
            error="report_not_found",
            message="Both scans must have completed reports",
        )

    def _core(doc: dict) -> dict:
        merged = dict(doc)
        if not merged.get("risk_triage"):
            merged["risk_triage"] = "unknown"
        if merged.get("probe_questions") is None:
            merged["probe_questions"] = []
        return {k: merged[k] for k in _REPORT_CORE_KEYS}

    try:
        ReportOutput.model_validate(_core(new_rep))
        ReportOutput.model_validate(_core(old_rep))
    except Exception:
        raise_api_error(
            status_code=400,
            error="report_invalid",
            message="Stored report is incomplete",
        )

    old_urls = await _urls_by_lane(db, previous_scan_id)
    new_urls = await _urls_by_lane(db, new_scan_id)

    changes: dict[str, dict[str, Any]] = {}
    new_signals: dict[str, list[str]] = {}
    for lane in ("litigation", "engineering", "hiring", "news"):
        prev_set = old_urls.get(lane, set())
        cur_set = new_urls.get(lane, set())
        added = sorted(cur_set - prev_set)
        new_signals[lane] = added
        n = len(added)
        if n == 0:
            summary = "No new sources vs previous scan."
        else:
            summary = f"{n} new source(s) vs previous scan."
        changes[lane] = {"new_chunks": n, "summary": summary}

    notable = await notable_changes_groq(
        _executive_summary(old_rep),
        _executive_summary(new_rep),
        new_signals,
    )

    ent = None
    if e_new:
        try:
            ent = await db.entities.find_one({"_id": ObjectId(e_new)})
        except Exception:
            ent = None
    entity_name = str((ent or {}).get("legal_name") or new_scan.get("legal_name") or "")

    v_old = str(old_rep.get("verdict") or "")
    v_new = str(new_rep.get("verdict") or "")

    scanned_at = new_scan.get("created_at")
    if isinstance(scanned_at, datetime):
        if scanned_at.tzinfo is None:
            scanned_at = scanned_at.replace(tzinfo=timezone.utc)
        else:
            scanned_at = scanned_at.astimezone(timezone.utc)
        scanned_iso = scanned_at.isoformat()
    else:
        scanned_iso = None

    return {
        "new_scan_id": new_scan_id,
        "previous_scan_id": previous_scan_id,
        "entity_name": entity_name,
        "scanned_at": scanned_iso,
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "verdict_changed": v_old != v_new,
        "verdict_before": v_old,
        "verdict_after": v_new,
        "changes": changes,
        "notable_changes": notable,
    }
