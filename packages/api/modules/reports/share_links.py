"""Shareable read-only report links (7-day TTL)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from rag.pipeline.llm_report_output import ensure_probe_questions
from rag.schema.llm_report import ReportOutput, insufficient_validation_fallback


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_or_reuse_share(
    db: Any,
    *,
    scan_id: str,
    user_id: str,
    entity_id: str,
    public_base_url: str,
) -> dict[str, Any]:
    active = await db.shared_reports.find_one(
        {
            "scan_id": scan_id,
            "created_by": user_id,
            "expires_at": {"$gt": _now()},
        }
    )
    if active:
        token = str(active["token"])
        exp = active["expires_at"]
        if isinstance(exp, datetime) and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return {
            "token": token,
            "expires_at": exp.isoformat(),
            "share_url": f"{public_base_url.rstrip('/')}/share/{token}",
        }
    token = secrets.token_hex(16)
    exp = _now() + timedelta(days=7)
    await db.shared_reports.insert_one(
        {
            "token": token,
            "scan_id": scan_id,
            "entity_id": entity_id,
            "created_by": user_id,
            "expires_at": exp,
            "view_count": 0,
            "created_at": _now(),
        }
    )
    return {
        "token": token,
        "expires_at": exp.isoformat(),
        "share_url": f"{public_base_url.rstrip('/')}/share/{token}",
    }


async def create_share_link_new(
    db: Any,
    *,
    scan_id: str,
    user_id: str,
    entity_id: str,
    public_base_url: str,
    ttl_days: int,
) -> dict[str, Any]:
    """Always insert a new share row (e.g. digest links with 30-day TTL)."""
    token = secrets.token_hex(16)
    exp = _now() + timedelta(days=ttl_days)
    await db.shared_reports.insert_one(
        {
            "token": token,
            "scan_id": scan_id,
            "entity_id": entity_id,
            "created_by": user_id,
            "expires_at": exp,
            "view_count": 0,
            "created_at": _now(),
        }
    )
    return {
        "token": token,
        "expires_at": exp.isoformat(),
        "share_url": f"{public_base_url.rstrip('/')}/share/{token}",
    }


async def fetch_shared_payload(db: Any, token: str) -> dict[str, Any] | None:
    doc = await db.shared_reports.find_one({"token": token})
    if not doc:
        return None
    exp = doc.get("expires_at")
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= _now():
            return None
    await db.shared_reports.update_one(
        {"_id": doc["_id"]},
        {"$inc": {"view_count": 1}},
    )
    scan_id = str(doc.get("scan_id") or "")
    entity_id = str(doc.get("entity_id") or "")
    rep = await db.reports.find_one({"scan_id": scan_id})
    if not rep:
        return None
    scan = None
    try:
        oid = ObjectId(scan_id)
        scan = await db.scans.find_one({"_id": oid})
    except (InvalidId, TypeError):
        pass
    ent = None
    if entity_id:
        try:
            ent = await db.entities.find_one({"_id": ObjectId(entity_id)})
        except (InvalidId, TypeError):
            ent = None
    entity_name = str((ent or {}).get("legal_name") or (scan or {}).get("legal_name") or "")
    created = (scan or {}).get("created_at") or rep.get("created_at")
    core_keys = (
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
    merged = dict(rep)
    if not merged.get("risk_triage"):
        merged["risk_triage"] = "unknown"
    if "probe_questions" not in merged or merged.get("probe_questions") is None:
        merged["probe_questions"] = []
    try:
        ro = ensure_probe_questions(ReportOutput.model_validate({k: merged[k] for k in core_keys}))
        dump = ro.model_dump(mode="python")
        report_body = {k: dump[k] for k in core_keys}
    except Exception:
        dump = insufficient_validation_fallback(parse_error="shared report invalid").model_dump(mode="python")
        report_body = {k: dump[k] for k in core_keys}
    return {
        "report": report_body,
        "entity_name": entity_name,
        "scan_date": created.isoformat() if isinstance(created, datetime) else str(created),
    }
