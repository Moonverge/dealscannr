from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from db.mongo import get_database
from modules.auth.deps import CurrentUser
from modules.entity.resolver import confirm_entity, resolve_entity
from rag.connectors.http_client import safe_get

router = APIRouter()


class ResolveBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, max_length=200)


class ConfirmBody(BaseModel):
    legal_name: str = Field(min_length=1, max_length=200)
    domain: str = Field(min_length=0, max_length=200)
    candidate_id: str | None = None


@router.get("/entity/autocomplete")
async def get_entity_autocomplete(
    user: CurrentUser,
    q: str = Query("", max_length=200),
) -> list[dict[str, Any]]:
    raw = (q or "").strip()
    if len(raw) < 2:
        return []
    try:
        resp = await safe_get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": raw},
            timeout=10.0,
        )
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return data


@router.post("/entity/resolve")
async def post_resolve(body: ResolveBody, user: CurrentUser):
    db = get_database()
    return await resolve_entity(db, name=body.name, domain_hint=body.domain_hint)


@router.post("/entity/confirm")
async def post_confirm(body: ConfirmBody, user: CurrentUser):
    db = get_database()
    return await confirm_entity(
        db,
        legal_name=body.legal_name,
        domain=body.domain or "",
        candidate_id=body.candidate_id,
    )
