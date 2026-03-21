def get_company_by_slug(slug: str):
    return {"slug": slug, "name": slug.replace("-", " ").title(), "report_cached": False}
