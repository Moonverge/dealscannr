from __future__ import annotations

import asyncio
import csv
import os
import io
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, UploadFile

from config.settings import settings
from db.mongo import get_database
from modules.api_errors import raise_api_error
from modules.auth.deps import CurrentUser, require_read_scope, require_scan_scope
from modules.credits.service import check_credits, get_credits_snapshot
from modules.entity.resolver import confirm_entity
from modules.reports.share_links import create_or_reuse_share
from modules.scans.pipeline import fail_scan, run_scan_pipeline
from middleware.rate_limit import check_scan_rate_limit
from outbound.digest import send_batch_complete_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


def _tier_ok(tier: str) -> bool:
    return tier in ("pro", "team")


async def _process_batch_job(batch_oid: ObjectId) -> None:
    db = get_database()
    job = await db.batch_jobs.find_one({"_id": batch_oid})
    if not job:
        return
    uid = job["user_id"]
    rl_sub = str(job.get("rate_limit_subject") or uid)
    user = await db.users.find_one({"_id": uid})
    email_to = str((user or {}).get("email") or "")
    rows: list[dict[str, Any]] = list(job.get("rows") or [])
    await db.batch_jobs.update_one(
        {"_id": batch_oid},
        {"$set": {"status": "running"}},
    )
    sem = asyncio.Semaphore(2)
    uid_str = str(uid)

    async def run_row(i: int, name: str, domain: str) -> None:
        async with sem:
            if not await check_credits(uid_str):
                await db.batch_jobs.update_one(
                    {"_id": batch_oid},
                    {
                        "$set": {
                            f"rows.{i}.status": "failed",
                            f"rows.{i}.error": "insufficient_credits",
                        },
                        "$inc": {"failed": 1},
                    },
                )
                return
            if not await check_scan_rate_limit(rl_sub):
                await db.batch_jobs.update_one(
                    {"_id": batch_oid},
                    {
                        "$set": {
                            f"rows.{i}.status": "failed",
                            f"rows.{i}.error": "rate_limited",
                        },
                        "$inc": {"failed": 1},
                    },
                )
                return
            try:
                resolved = await confirm_entity(
                    db,
                    legal_name=name.strip(),
                    domain=(domain or "").strip(),
                    candidate_id=None,
                )
                eid = resolved["entity_id"]
                legal = str(resolved.get("legal_name") or name.strip())
                dom = str(resolved.get("domain") or "")
                now = datetime.now(timezone.utc)
                ins = await db.scans.insert_one(
                    {
                        "user_id": uid,
                        "entity_id": eid,
                        "legal_name": legal,
                        "domain": dom,
                        "status": "running",
                        "created_at": now,
                        "credits_used": 0,
                        "lane_coverage": 0,
                    }
                )
                scan_id = str(ins.inserted_id)
                try:
                    await run_scan_pipeline(
                        scan_id=scan_id,
                        entity_id=eid,
                        legal_name=legal,
                        domain=dom,
                        user_id=uid_str,
                        skip_credit_deduct=False,
                    )
                except Exception as e:
                    logger.exception("batch_scan_failed row=%s", i)
                    await fail_scan(scan_id, str(e))
                    await db.batch_jobs.update_one(
                        {"_id": batch_oid},
                        {
                            "$set": {
                                f"rows.{i}.status": "failed",
                                f"rows.{i}.scan_id": scan_id,
                                f"rows.{i}.error": str(e)[:200],
                            },
                            "$inc": {"failed": 1},
                        },
                    )
                    return
                rep = await db.reports.find_one({"scan_id": scan_id})
                verdict = str(rep.get("verdict") or "INSUFFICIENT") if rep else "INSUFFICIENT"
                await db.batch_jobs.update_one(
                    {"_id": batch_oid},
                    {
                        "$set": {
                            f"rows.{i}.status": "complete",
                            f"rows.{i}.scan_id": scan_id,
                            f"rows.{i}.verdict": verdict,
                            f"rows.{i}.entity_id": eid,
                        },
                        "$inc": {"completed": 1},
                    },
                )
            except Exception as e:
                logger.exception("batch_row_failed i=%s", i)
                await db.batch_jobs.update_one(
                    {"_id": batch_oid},
                    {
                        "$set": {
                            f"rows.{i}.status": "failed",
                            f"rows.{i}.error": str(e)[:200],
                        },
                        "$inc": {"failed": 1},
                    },
                )

    tasks = [run_row(i, str(r.get("name") or ""), str(r.get("domain") or "")) for i, r in enumerate(rows)]
    await asyncio.gather(*tasks)
    now = datetime.now(timezone.utc)
    await db.batch_jobs.update_one(
        {"_id": batch_oid},
        {"$set": {"status": "complete", "completed_at": now}},
    )

    job2 = await db.batch_jobs.find_one({"_id": batch_oid})
    rows2 = list((job2 or {}).get("rows") or [])
    email_rows: list[dict[str, Any]] = []
    for r in rows2:
        if r.get("status") != "complete" or not r.get("scan_id"):
            continue
        eid_row = str(r.get("entity_id") or "")
        share = await create_or_reuse_share(
            db,
            scan_id=str(r["scan_id"]),
            user_id=uid_str,
            entity_id=eid_row,
            public_base_url=settings.public_app_url,
        )
        email_rows.append(
            {
                "company_name": r.get("name"),
                "verdict": r.get("verdict"),
                "report_url": share["share_url"],
            }
        )
    if email_to and email_rows:
        await send_batch_complete_email(email_to, email_rows)


@router.post("")
async def upload_batch(user: CurrentUser, file: UploadFile = File(...)):
    require_scan_scope(user)
    from modules.credits.service import PLAN_BATCH_MAX_ROWS

    tier = str(user.get("plan_tier") or "free")
    if not _tier_ok(tier):
        raise_api_error(
            status_code=403,
            error="plan_required",
            message="Batch scan requires Pro or Team",
        )
    max_rows = PLAN_BATCH_MAX_ROWS.get(tier, 0)
    raw = (await file.read()).decode("utf-8", errors="replace").lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(raw))
    fields = reader.fieldnames or []
    norm = {f.strip().lower(): f.strip() for f in fields}
    if "company_name" not in norm:
        raise_api_error(
            status_code=400,
            error="invalid_csv",
            message="CSV must include a company_name column",
        )
    name_col = norm["company_name"]
    domain_col = norm.get("domain")
    parsed: list[tuple[str, str]] = []
    for row in reader:
        nm = str(row.get(name_col) or "").strip()
        if not nm:
            continue
        dom = str(row.get(domain_col) or "").strip() if domain_col else ""
        parsed.append((nm, dom))
        if len(parsed) > max_rows:
            raise_api_error(
                status_code=400,
                error="too_many_rows",
                message=f"Maximum {max_rows} rows for your plan",
            )
    if not parsed:
        raise_api_error(status_code=400, error="empty_csv", message="No data rows")

    snap = await get_credits_snapshot(str(user["_id"]))
    if int(snap.get("remaining") or 0) < len(parsed):
        raise_api_error(
            status_code=402,
            error="credits_exhausted",
            message="Not enough scan credits for this batch",
        )

    db = get_database()
    now = datetime.now(timezone.utc)
    rows = [
        {
            "name": nm,
            "domain": dom,
            "scan_id": None,
            "verdict": None,
            "status": "pending",
            "error": None,
            "entity_id": "",
        }
        for nm, dom in parsed
    ]
    ins = await db.batch_jobs.insert_one(
        {
            "user_id": user["_id"],
            "rate_limit_subject": user.get("_rate_limit_sub") or str(user["_id"]),
            "total": len(rows),
            "completed": 0,
            "failed": 0,
            "status": "queued",
            "rows": rows,
            "created_at": now,
            "completed_at": None,
        }
    )
    bid = str(ins.inserted_id)
    if os.environ.get("TEST_BATCH_SYNC") == "1":
        await _process_batch_job(ins.inserted_id)
    else:
        asyncio.create_task(_process_batch_job(ins.inserted_id))
    return {"batch_id": bid, "total": len(rows), "status": "queued"}


@router.get("/{batch_id}")
async def batch_status(batch_id: str, user: CurrentUser):
    require_read_scope(user)
    try:
        oid = ObjectId(batch_id)
    except InvalidId:
        raise_api_error(status_code=404, error="not_found", message="Invalid batch id")
    db = get_database()
    job = await db.batch_jobs.find_one({"_id": oid})
    if not job or job.get("user_id") != user["_id"]:
        raise_api_error(status_code=404, error="not_found", message="Batch not found")
    rows = job.get("rows") or []
    results = [
        {
            "company_name": r.get("name"),
            "domain": r.get("domain"),
            "scan_id": r.get("scan_id"),
            "verdict": r.get("verdict"),
            "status": r.get("status"),
            "error": r.get("error"),
        }
        for r in rows
    ]
    return {
        "batch_id": batch_id,
        "total": job.get("total", 0),
        "completed": job.get("completed", 0),
        "failed": job.get("failed", 0),
        "status": job.get("status", "unknown"),
        "results": results,
    }
