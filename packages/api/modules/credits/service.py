"""Scan credits: monthly bucket on user doc + immutable ledger."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from db.mongo import get_database

logger = logging.getLogger(__name__)

PLAN_MONTHLY_LIMITS: dict[str, int] = {
    "free": 3,
    "pro": 50,
    "team": 200,
}

PLAN_WATCHLIST_LIMITS: dict[str, int] = {
    "free": 10,
    "pro": 50,
    "team": 100,
}

PLAN_BATCH_MAX_ROWS: dict[str, int] = {
    "free": 0,
    "pro": 20,
    "team": 50,
}


def _month_key(dt: datetime) -> str:
    return f"{dt.year}-{dt.month:02d}"


def _next_month_start_utc(now: datetime) -> datetime:
    y, m = now.year, now.month
    if m == 12:
        return datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(y, m + 1, 1, tzinfo=timezone.utc)


async def _load_user(db: Any, user_id: str) -> dict[str, Any] | None:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return await db.users.find_one({"_id": oid})


async def ensure_monthly_reset(db: Any, user: dict[str, Any]) -> dict[str, Any]:
    """Reset scan_credits to plan limit when UTC month changes."""
    now = datetime.now(timezone.utc)
    key = _month_key(now)
    if user.get("credits_period") == key:
        return user
    tier = str(user.get("plan_tier") or "free")
    limit = PLAN_MONTHLY_LIMITS.get(tier, PLAN_MONTHLY_LIMITS["free"])
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"credits_period": key, "scan_credits": limit}},
    )
    user["credits_period"] = key
    user["scan_credits"] = limit
    return user


async def check_credits(user_id: str) -> bool:
    db = get_database()
    user = await _load_user(db, user_id)
    if not user:
        return False
    user = await ensure_monthly_reset(db, user)
    credits = int(user.get("scan_credits") or 0)
    return credits > 0


async def deduct_credit(user_id: str, scan_id: str) -> bool:
    db = get_database()
    user = await _load_user(db, user_id)
    if not user:
        return False
    user = await ensure_monthly_reset(db, user)
    uid = user["_id"]
    exists = await db.credit_ledger.find_one(
        {"user_id": str(uid), "scan_id": scan_id, "action": "deduct"},
    )
    if exists:
        return False
    cur = int(user.get("scan_credits") or 0)
    if cur <= 0:
        return False
    new_bal = cur - 1
    try:
        await db.credit_ledger.insert_one(
            {
                "user_id": str(uid),
                "scan_id": scan_id,
                "action": "deduct",
                "amount": -1,
                "balance_after": new_bal,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as e:
        logger.warning("credit_ledger_deduct_insert_failed: %s", e)
        return False
    await db.users.update_one({"_id": uid}, {"$set": {"scan_credits": new_bal}})
    return True


async def refund_credit(user_id: str, scan_id: str, reason: str) -> bool:
    db = get_database()
    user = await _load_user(db, user_id)
    if not user:
        return False
    user = await ensure_monthly_reset(db, user)
    uid = user["_id"]
    if await db.credit_ledger.find_one(
        {"user_id": str(uid), "scan_id": scan_id, "action": "refund"},
    ):
        return False
    deduct = await db.credit_ledger.find_one(
        {"user_id": str(uid), "scan_id": scan_id, "action": "deduct"},
    )
    if not deduct:
        return False
    cur = int(user.get("scan_credits") or 0)
    tier = str(user.get("plan_tier") or "free")
    limit = PLAN_MONTHLY_LIMITS.get(tier, PLAN_MONTHLY_LIMITS["free"])
    new_bal = min(limit, cur + 1)
    try:
        await db.credit_ledger.insert_one(
            {
                "user_id": str(uid),
                "scan_id": scan_id,
                "action": "refund",
                "amount": 1,
                "reason": reason[:500],
                "balance_after": new_bal,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as e:
        logger.warning("credit_ledger_refund_insert_failed: %s", e)
        return False
    await db.users.update_one({"_id": uid}, {"$set": {"scan_credits": new_bal}})
    return True


async def get_credits_snapshot(user_id: str) -> dict[str, Any]:
    db = get_database()
    user = await _load_user(db, user_id)
    if not user:
        raise ValueError("user_not_found")
    user = await ensure_monthly_reset(db, user)
    tier = str(user.get("plan_tier") or "free")
    limit = PLAN_MONTHLY_LIMITS.get(tier, PLAN_MONTHLY_LIMITS["free"])
    remaining = int(user.get("scan_credits") or 0)
    monthly_used = max(0, limit - remaining)
    now = datetime.now(timezone.utc)
    return {
        "remaining": remaining,
        "plan": tier,
        "monthly_used": monthly_used,
        "monthly_limit": limit,
        "resets_at": _next_month_start_utc(now).isoformat(),
    }
