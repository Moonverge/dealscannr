from fastapi import APIRouter
from modules.companies.controller import handle_get_company

router = APIRouter()


@router.get("/companies/{slug}")
def get_company(slug: str):
    return handle_get_company(slug)
