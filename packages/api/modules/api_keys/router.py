from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from db.mongo import get_database
from modules.api_errors import raise_api_error
from modules.auth.deps import CurrentUserJwt
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/keys", tags=["api-keys"])

MAX_KEYS_PER_USER = 5
KEY_PREFIX = "ds_live_"


class CreateKeyBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[Literal["scan", "read"]] = Field(default_factory=lambda: ["scan", "read"])


def _tier_ok(tier: str) -> bool:
    return tier in ("pro", "team")


def _norm_scopes(scopes: list[str]) -> list[str]:
    out = [s for s in scopes if s in ("scan", "read")]
    return out if out else ["scan", "read"]


@router.post("")
async def create_key(body: CreateKeyBody, user: CurrentUserJwt):
    tier = str(user.get("plan_tier") or "free")
    if not _tier_ok(tier):
        raise_api_error(
            status_code=403,
            error="plan_required",
            message="API keys require Pro or Team",
        )
    db = get_database()
    n = await db.api_keys.count_documents({"user_id": user["_id"], "is_active": True})
    if n >= MAX_KEYS_PER_USER:
        raise_api_error(
            status_code=400,
            error="key_limit",
            message=f"Maximum {MAX_KEYS_PER_USER} API keys",
        )
    raw = secrets.token_hex(16)
    full = f"{KEY_PREFIX}{raw}"
    key_hash = hashlib.sha256(full.encode("utf-8")).hexdigest()
    key_prefix = f"{KEY_PREFIX}{raw[:8]}"
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user["_id"],
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "name": body.name.strip()[:120],
        "scopes": _norm_scopes(list(body.scopes)),
        "created_at": now,
        "last_used_at": None,
        "is_active": True,
    }
    try:
        await db.api_keys.insert_one(doc)
    except DuplicateKeyError:
        raise_api_error(status_code=409, error="conflict", message="Key collision — retry")
    return {
        "key": full,
        "prefix": key_prefix,
        "name": doc["name"],
        "scopes": doc["scopes"],
        "created_at": now.isoformat(),
    }


@router.get("")
async def list_keys(user: CurrentUserJwt):
    db = get_database()
    cursor = db.api_keys.find({"user_id": user["_id"], "is_active": True}).sort("created_at", -1)
    rows = await cursor.to_list(length=20)
    return {
        "keys": [
            {
                "prefix": r.get("key_prefix"),
                "name": r.get("name"),
                "created_at": r.get("created_at"),
                "last_used_at": r.get("last_used_at"),
                "scopes": r.get("scopes") or [],
            }
            for r in rows
        ]
    }


@router.delete("/{key_prefix:path}")
async def delete_key(key_prefix: str, user: CurrentUserJwt):
    db = get_database()
    p = key_prefix.strip()
    if not p.startswith(KEY_PREFIX):
        raise_api_error(status_code=400, error="invalid_prefix", message="Invalid key prefix")
    res = await db.api_keys.update_one(
        {"user_id": user["_id"], "key_prefix": p, "is_active": True},
        {"$set": {"is_active": False}},
    )
    if res.matched_count == 0:
        raise_api_error(status_code=404, error="not_found", message="Key not found")
    return {"ok": True}
