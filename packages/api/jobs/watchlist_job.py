"""Weekly watchlist rescans + optional digest email."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from config.settings import settings
from db.mongo import get_database
from modules.reports.share_links import create_share_link_new
from modules.scans.diff_service import compute_scan_diff
from modules.scans.pipeline import fail_scan, run_scan_pipeline
from outbound.digest import DigestItem, send_watchlist_digest

logger = logging.getLogger(__name__)


def _notify_matches(notify_on: list[str] | None, verdict: str, verdict_changed: bool) -> bool:
    n = notify_on if notify_on else ["all"]
    if "all" in n:
        return True
    if "verdict_change" in n and verdict_changed:
        return True
    if "flag_detected" in n and verdict.upper() == "FLAG":
        return True
    return False


async def run_watchlist_digest() -> None:
    db = get_database()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    q: dict[str, Any] = {
        "$or": [
            {"last_scanned_at": {"$exists": False}},
            {"last_scanned_at": None},
            {"last_scanned_at": {"$lt": week_ago}},
        ]
    }
    entries = await db.watchlist.find(q).to_list(length=3000)
    if not entries:
        return

    by_user: defaultdict[ObjectId, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        uid = e.get("user_id")
        if isinstance(uid, ObjectId):
            by_user[uid].append(e)

    for uid, elist in by_user.items():
        user = await db.users.find_one({"_id": uid})
        if not user:
            continue
        email_to = str(user.get("email") or "")
        if not email_to:
            continue

        digest_items: list[DigestItem] = []

        for entry in elist:
            eid = str(entry.get("entity_id") or "")
            if not eid:
                continue
            legal = str(entry.get("entity_name") or "")
            domain = str(entry.get("domain") or "")
            scan_doc = {
                "user_id": uid,
                "entity_id": eid,
                "legal_name": legal,
                "domain": domain,
                "status": "running",
                "created_at": datetime.now(timezone.utc),
                "credits_used": 0,
                "lane_coverage": 0,
            }
            ins = await db.scans.insert_one(scan_doc)
            scan_id = str(ins.inserted_id)
            verdict = "INSUFFICIENT"
            try:
                await run_scan_pipeline(
                    scan_id=scan_id,
                    entity_id=eid,
                    legal_name=legal,
                    domain=domain,
                    user_id=str(uid),
                    skip_credit_deduct=True,
                )
            except Exception as e:
                logger.exception("watchlist_pipeline_failed scan_id=%s", scan_id)
                await fail_scan(scan_id, str(e))
                await db.watchlist.update_one(
                    {"_id": entry["_id"]},
                    {"$set": {"last_scanned_at": now, "last_verdict": "INSUFFICIENT"}},
                )
                continue

            rep = await db.reports.find_one({"scan_id": scan_id})
            verdict = str(rep.get("verdict") or "INSUFFICIENT") if rep else "INSUFFICIENT"

            cur = await db.scans.find_one({"_id": ObjectId(scan_id)})
            prev = None
            if cur and isinstance(cur.get("created_at"), datetime):
                prev = await db.scans.find_one(
                    {
                        "user_id": uid,
                        "entity_id": eid,
                        "created_at": {"$lt": cur["created_at"]},
                    },
                    sort=[("created_at", -1)],
                )

            notable: list[str] = []
            verdict_changed = False
            prev_v: str | None = None
            if prev:
                try:
                    diff = await compute_scan_diff(
                        user_id=uid,
                        new_scan_id=scan_id,
                        previous_scan_id=str(prev["_id"]),
                    )
                    notable = list((diff.get("notable_changes") or [])[:3])
                    verdict_changed = bool(diff.get("verdict_changed"))
                    prev_v = str(diff.get("verdict_before") or "") or None
                except Exception as ex:
                    logger.warning("watchlist_diff_failed scan=%s err=%s", scan_id, ex)

            share = await create_share_link_new(
                db,
                scan_id=scan_id,
                user_id=str(uid),
                entity_id=eid,
                public_base_url=settings.public_app_url,
                ttl_days=30,
            )

            if _notify_matches(entry.get("notify_on"), verdict, verdict_changed):
                digest_items.append(
                    DigestItem(
                        entity_name=legal or str(entry.get("entity_name") or ""),
                        domain=domain,
                        verdict=verdict,
                        verdict_changed=verdict_changed,
                        previous_verdict=prev_v,
                        notable_changes=notable,
                        report_url=share["share_url"],
                        scan_date=now,
                    )
                )

            await db.watchlist.update_one(
                {"_id": entry["_id"]},
                {"$set": {"last_scanned_at": now, "last_verdict": verdict}},
            )

        if digest_items:
            await send_watchlist_digest(
                user_email=email_to,
                user_name=email_to.split("@")[0],
                digest_items=digest_items,
            )
