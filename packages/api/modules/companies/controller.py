from modules.companies.service import get_company_by_slug


def handle_get_company(slug: str):
    return get_company_by_slug(slug)
