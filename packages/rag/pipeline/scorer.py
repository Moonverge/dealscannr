import json
import re
from typing import Literal


def parse_verdict_from_llm(raw: str) -> tuple[Literal["green", "yellow", "red"], float]:
    raw = raw.strip()
    try:
        if "```" in raw:
            raw = re.sub(r"^```\w*\n?", "", raw).split("```")[0].strip()
        data = json.loads(raw)
        v = (data.get("verdict") or "yellow").lower()
        if v not in ("green", "yellow", "red"):
            v = "yellow"
        c = float(data.get("confidence", 0.5))
        c = max(0.0, min(1.0, c))
        return v, c
    except Exception:
        return "yellow", 0.5
