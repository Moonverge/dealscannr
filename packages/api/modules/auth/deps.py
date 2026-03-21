from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Annotated, Any

import jwt
from bson import ObjectId
from bson.errors import InvalidId as BsonInvalidId
from fastapi import Depends, Header

from config.settings import settings
from db.mongo import get_database
from modules.api_errors import raise_api_error


def _db():
    return get_database()


def rate_limit_subject(user: dict[str, Any]) -> str:
    return str(user.get("_rate_limit_sub") or user["_id"])


async def _user_from_jwt(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid or expired token",
        )
    sub = payload.get("sub")
    if not sub:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid token subject",
        )
    try:
        oid = ObjectId(str(sub))
    except BsonInvalidId:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid user id in token",
        )
    db = _db()
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="User no longer exists",
        )
    return user


async def _user_from_api_key(raw_key: str) -> dict[str, Any]:
    if not raw_key.startswith("ds_live_") or len(raw_key) < 20:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid API key",
        )
    h = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    db = _db()
    rec = await db.api_keys.find_one({"key_hash": h, "is_active": True})
    if not rec:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Invalid API key",
        )
    user = await db.users.find_one({"_id": rec["user_id"]})
    if not user:
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="User no longer exists",
        )
    await db.api_keys.update_one(
        {"_id": rec["_id"]},
        {"$set": {"last_used_at": datetime.now(timezone.utc)}},
    )
    u = dict(user)
    u["_rate_limit_sub"] = f"apikey:{h[:20]}"
    u["_api_scopes"] = list(rec.get("scopes") or ["scan", "read"])
    return u


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise_api_error(
            status_code=401,
            error="unauthorized",
            message="Missing or invalid Authorization header",
        )
    raw = authorization.split(" ", 1)[1].strip()
    if raw.startswith("ds_live_"):
        return await _user_from_api_key(raw)
    return await _user_from_jwt(raw)


def require_jwt_user(user: dict[str, Any]) -> None:
    """Reject API-key auth (e.g. billing UI flows)."""
    if user.get("_api_scopes") is not None:
        raise_api_error(
            status_code=403,
            error="forbidden",
            message="This action requires a logged-in session",
        )


def require_scan_scope(user: dict[str, Any]) -> None:
    sc = user.get("_api_scopes")
    if sc is not None and "scan" not in sc:
        raise_api_error(
            status_code=403,
            error="forbidden",
            message="Missing scan scope",
        )


def require_read_scope(user: dict[str, Any]) -> None:
    sc = user.get("_api_scopes")
    if sc is not None and "read" not in sc:
        raise_api_error(
            status_code=403,
            error="forbidden",
            message="Missing read scope",
        )


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


async def get_jwt_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    u = await get_current_user(authorization)
    require_jwt_user(u)
    return u


CurrentUserJwt = Annotated[dict[str, Any], Depends(get_jwt_user)]
