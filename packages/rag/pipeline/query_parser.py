import re
from dataclasses import dataclass


@dataclass
class ParsedQuery:
    entity: str
    intent: str


def parse_query(query: str) -> ParsedQuery:
    q = (query or "").strip()
    if not q:
        return ParsedQuery(entity="", intent="full_due_diligence")
    entity = q[:200].strip()
    for pair in (('"', '"'), ("'", "'"), ("`", "`"), ("\u201c", "\u201d")):
        if len(entity) >= 2 and entity.startswith(pair[0]) and entity.endswith(pair[1]):
            entity = entity[1:-1].strip()
            break
    entity = entity.strip("'\"").strip()
    intent = "full_due_diligence"
    return ParsedQuery(entity=entity, intent=intent)
