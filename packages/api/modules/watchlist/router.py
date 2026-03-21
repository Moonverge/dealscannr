from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter
from pydantic import BaseModel, Field

from db.mongo import get_database
from modules.api_errors import raise_api_error
from modules.auth.deps import CurrentUserJwt
router = APIRouter(prefix="/watchlist", tags=["watchlist"])

NotifyLiteral = Literal["all", "verdict_change", "flag_detected"]


class WatchlistAddBody(BaseModel):
    entity_id: str = Field(min_length=1, max_length=128)
    notify_on: list[str] = Field(default_factory=lambda: ["all"])


class WatchlistPatchBody(BaseModel):
    notify_on: list[str]


def _tier(user: dict[str, Any]) -> str:
    return str(user.get("plan_tier") or "free")


def _limit_for(user: dict[str, Any]) -> int:
    from modules.credits.service import PLAN_WATCHLIST_LIMITS

    return PLAN_WATCHLIST_LIMITS.get(_tier(user), PLAN_WATCHLIST_LIMITS["free"])


def _validate_notify(vals: list[str]) -> list[str]:
    allowed = {"all", "verdict_change", "flag_detected"}
    out = [v for v in vals if v in allowed]
    return out if out else ["all"]


@router.post("")
async def add_watchlist(body: WatchlistAddBody, user: CurrentUserJwt):
    db = get_database()
    lim = _limit_for(user)
    cnt = await db.watchlist.count_documents({"user_id": user["_id"]})
    if cnt >= lim:
        raise_api_error(
            status_code=400,
            error="watchlist_limit",
            message=f"Watchlist full for your plan ({lim} max)",
        )
    eid = body.entity_id.strip()
    try:
        ent_oid = ObjectId(eid)
    except InvalidId:
        raise_api_error(status_code=400, error="invalid_entity", message="Invalid entity id")
    ent = await db.entities.find_one({"_id": ent_oid})
    if not ent:
        raise_api_error(status_code=404, error="entity_not_found", message="Entity not found")
    from pymongo.errors import DuplicateKeyError

    doc = {
        "user_id": user["_id"],
        "entity_id": eid,
        "entity_name": str(ent.get("legal_name") or ""),
        "domain": str(ent.get("domain") or ""),
        "added_at": datetime.now(timezone.utc),
        "last_scanned_at": None,
        "last_verdict": None,
        "notify_on": _validate_notify(body.notify_on),
    }
    try:
        ins = await db.watchlist.insert_one(doc)
    except DuplicateKeyError:
        raise_api_error(
            status_code=409,
            error="duplicate_watchlist",
            message="Already watching this company",
        )
    doc["_id"] = ins.inserted_id
    return _serialize_entry(doc)


@router.get("")
async def list_watchlist(user: CurrentUserJwt):
    db = get_database()
    cursor = db.watchlist.find({"user_id": user["_id"]}).sort("added_at", -1)
    rows = await cursor.to_list(length=200)
    return {"entries": [_serialize_entry(r) for r in rows]}


@router.delete("/{entity_id}")
async def remove_watchlist(entity_id: str, user: CurrentUserJwt):
    db = get_database()
    res = await db.watchlist.delete_one({"user_id": user["_id"], "entity_id": entity_id.strip()})
    if res.deleted_count == 0:
        raise_api_error(status_code=404, error="not_found", message="Watchlist entry not found")
    return {"ok": True}


@router.patch("/{entity_id}")
async def patch_watchlist(entity_id: str, body: WatchlistPatchBody, user: CurrentUserJwt):
    db = get_database()
    eid = entity_id.strip()
    notify = _validate_notify(body.notify_on)
    res = await db.watchlist.update_one(
        {"user_id": user["_id"], "entity_id": eid},
        {"$set": {"notify_on": notify}},
    )
    if res.matched_count == 0:
        raise_api_error(status_code=404, error="not_found", message="Watchlist entry not found")
    doc = await db.watchlist.find_one({"user_id": user["_id"], "entity_id": eid})
    return _serialize_entry(doc or {})


def _serialize_entry(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("_id")),
        "entity_id": str(r.get("entity_id") or ""),
        "entity_name": str(r.get("entity_name") or ""),
        "domain": str(r.get("domain") or ""),
        "added_at": r.get("added_at"),
        "last_scanned_at": r.get("last_scanned_at"),
        "last_verdict": r.get("last_verdict"),
        "notify_on": r.get("notify_on") or ["all"],
    }
