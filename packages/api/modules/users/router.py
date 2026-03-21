from fastapi import APIRouter

from modules.api_errors import raise_api_error
from modules.auth.deps import CurrentUser, require_read_scope
from modules.credits.service import get_credits_snapshot

router = APIRouter()


@router.get("/users/me/credits")
async def get_my_credits(user: CurrentUser):
    require_read_scope(user)
    try:
        return await get_credits_snapshot(str(user["_id"]))
    except ValueError:
        raise_api_error(
            status_code=404,
            error="not_found",
            message="User not found",
        )
