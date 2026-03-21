import json
import re
from datetime import datetime
from typing import Any

from rag.schema import IntelligenceReport, Signal, SignalCategory


def _parse_llm_report_json(raw: str, company_name: str) -> dict[str, Any]:
    # Strip markdown code block if present
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = re.sub(r"^```\w*\n?", "", text).split("```")[0].strip()
    return json.loads(text)


def build_report_from_llm_response(
    raw_response: str,
    company_name: str,
    verdict: str = "yellow",
    confidence: float = 0.5,
    sources_used: list[str] | None = None,
    raw_chunks_count: int = 0,
) -> IntelligenceReport:
    try:
        data = _parse_llm_report_json(raw_response, company_name)
    except (json.JSONDecodeError, KeyError):
        return IntelligenceReport(
            company_name=company_name,
            generated_at=datetime.utcnow(),
            verdict=verdict,
            confidence=confidence,
            summary="Unable to parse structured report from context.",
            signals=[],
            sources_used=sources_used or [],
            raw_chunks_count=raw_chunks_count,
        )

    signals: list[Signal] = []
    for s in data.get("signals", []):
        try:
            cat = s.get("category", "product")
            if isinstance(cat, str) and cat.upper() in SignalCategory.__members__:
                category = SignalCategory[cat.upper()]
            else:
                category = SignalCategory.PRODUCT
            signals.append(
                Signal(
                    category=category,
                    title=str(s.get("title", ""))[:200],
                    description=str(s.get("description", ""))[:2000],
                    sentiment=s.get("sentiment", "neutral") if s.get("sentiment") in ("positive", "negative", "neutral") else "neutral",
                    source=str(s.get("source", "Unknown"))[:200],
                    weight=float(s.get("weight", 0.5)),
                )
            )
        except Exception:
            continue

    return IntelligenceReport(
        company_name=data.get("company_name", company_name),
        generated_at=datetime.utcnow(),
        verdict=data.get("verdict", verdict),
        confidence=float(data.get("confidence", confidence)),
        summary=str(data.get("summary", ""))[:2000],
        signals=signals,
        sources_used=list(data.get("sources_used", sources_used or [])),
        raw_chunks_count=raw_chunks_count,
    )
