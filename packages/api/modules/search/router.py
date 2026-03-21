from fastapi import APIRouter
from pydantic import BaseModel

from modules.api_errors import raise_api_error
from modules.search.controller import handle_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = ""
    company_name: str | None = None


@router.post("/search")
def post_search(body: SearchRequest):
    q = (body.company_name or body.query or "").strip()
    if not q:
        raise_api_error(
            status_code=422,
            error="validation_error",
            message="query or company_name required",
        )
    report = handle_search(q)
    return report.model_dump(mode="json")
