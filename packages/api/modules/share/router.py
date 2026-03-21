from fastapi import APIRouter

from db.mongo import get_database
from modules.api_errors import raise_api_error
from modules.reports.share_links import fetch_shared_payload

router = APIRouter()


@router.get("/share/{token}")
async def get_shared_report(token: str):
    db = get_database()
    payload = await fetch_shared_payload(db, token)
    if not payload:
        raise_api_error(
            status_code=404,
            error="share_expired",
            message="Share link is invalid or has expired",
        )
    return payload
