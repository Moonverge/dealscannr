import re


def format_company_display_name(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return s
    parts = re.split(r"(\s+|[\-&/])", s)
    out: list[str] = []
    for p in parts:
        if not p or re.fullmatch(r"[\s\-&/]+", p):
            out.append(p)
        elif len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p[0].upper() + p[1:].lower())
    return "".join(out)
