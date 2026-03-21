"""Parse Groq JSON, validate ReportOutput, strip hallucinated chunk citations."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from rag.schema.llm_report import (
    DEFAULT_PROBE_QUESTIONS,
    REPORT_SECTION_KEYS,
    ReportOutput,
    ReportSection,
    insufficient_validation_fallback,
)

logger = logging.getLogger(__name__)

_CHUNK_ID_PREFIX = "chunk_id:"


def _clean_citation_id(raw: str) -> str:
    """Normalize LLM citation strings (strip accidental repeated 'chunk_id:' prefixes)."""
    cleaned = raw.strip()
    while cleaned.lower().startswith(_CHUNK_ID_PREFIX):
        cleaned = cleaned[len(_CHUNK_ID_PREFIX) :].lstrip()
    return cleaned


def _apply_verdict_floor(report: ReportOutput) -> ReportOutput:
    """Downgrade verdicts when confidence is inconsistent with the label."""
    c = float(report.confidence_score)
    v = report.verdict
    if c == 0.0:
        v = "INSUFFICIENT"
    else:
        if v == "MEET" and c < 0.4:
            v = "PASS"
        if v == "FLAG" and c < 0.25:
            v = "PASS"
        if v == "PASS" and c < 0.15:
            v = "INSUFFICIENT"
    if v != report.verdict:
        return report.model_copy(update={"verdict": v})
    return report


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = re.sub(r"^```\w*\n?", "", text).split("```", 1)[0].strip()
    return json.loads(text)


def _split_probes_from_executive_text(text: str) -> tuple[str, list[str]]:
    """If the model embedded probes in executive text, extract them."""
    parts = re.split(r"\n\s*Before the call, probe:\s*", text, maxsplit=1, flags=re.I | re.DOTALL)
    if len(parts) < 2:
        return (text.strip(), [])
    narrative = (parts[0] or "").strip()
    block = (parts[1] or "").strip()
    lines: list[str] = []
    for line in block.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[•\-\*]\s*", "", line).strip()
        if line:
            lines.append(line)
    return narrative, lines


def ensure_probe_questions(report: ReportOutput) -> ReportOutput:
    """Guarantee three call probes: model array, then embedded text, then defaults."""
    pq = [q.strip() for q in report.probe_questions if q.strip()]
    exec_sec = report.sections.get("executive_summary")
    ex_text = (exec_sec.text if exec_sec else "") or ""
    narrative, from_text = _split_probes_from_executive_text(ex_text)
    for q in from_text:
        if len(pq) >= 3:
            break
        if q and q not in pq:
            pq.append(q)
    while len(pq) < 3:
        pq.append(DEFAULT_PROBE_QUESTIONS[len(pq)])
    new_pq = pq[:3]
    if (
        exec_sec
        and narrative
        and narrative != ex_text
        and "before the call, probe" in ex_text.lower()
    ):
        sections = dict(report.sections)
        sections["executive_summary"] = ReportSection(
            text=narrative,
            citations=list(exec_sec.citations),
            status=exec_sec.status,
        )
        return report.model_copy(update={"probe_questions": new_pq, "sections": sections})
    return report.model_copy(update={"probe_questions": new_pq})


def _strip_hallucinated_citations(
    report: ReportOutput,
    valid_chunk_ids: set[str],
) -> tuple[ReportOutput, int]:
    removed = 0
    new_sections: dict[str, ReportSection] = {}
    for key in REPORT_SECTION_KEYS:
        sec = report.sections[key]
        kept: list[str] = []
        for c in sec.citations:
            cid = _clean_citation_id(c)
            if cid in valid_chunk_ids:
                kept.append(cid)
            else:
                removed += 1
                logger.warning(
                    "hallucinated_chunk_citation section=%s citation=%s",
                    key,
                    c,
                )
        new_sections[key] = ReportSection(
            text=sec.text,
            citations=kept,
            status=sec.status,
        )
    conf = float(report.confidence_score) - 0.1 * removed
    if conf < 0.0:
        conf = 0.0
    return (
        report.model_copy(
            update={
                "sections": new_sections,
                "confidence_score": conf,
            }
        ),
        removed,
    )


def parse_validate_report_output(
    raw_llm: str,
    valid_chunk_ids: set[str],
) -> tuple[ReportOutput, int]:
    """
    1) Parse JSON
    2) ReportOutput(**parsed) or INSUFFICIENT fallback + log
    3) Strip citations not in valid_chunk_ids; decrement confidence 0.1 per removed
    Returns (report, hallucinated_citations_count).
    """
    if not raw_llm.strip():
        logger.error("llm_report_empty_response")
        return insufficient_validation_fallback(parse_error="empty response"), 0
    try:
        data = _parse_llm_json(raw_llm)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("llm_report_json_parse_failed raw_prefix=%s err=%s", raw_llm[:400], e)
        return insufficient_validation_fallback(parse_error=str(e)), 0
    try:
        report = ReportOutput(**data)
    except ValidationError as e:
        logger.error("llm_report_validation_failed: %s raw_prefix=%s", e, raw_llm[:400])
        return insufficient_validation_fallback(parse_error=str(e)), 0
    sanitized, removed = _strip_hallucinated_citations(report, valid_chunk_ids)
    if removed >= 3:
        c = float(sanitized.confidence_score) - 0.2
        sanitized = sanitized.model_copy(update={"confidence_score": max(0.0, c)})
    sanitized = _apply_verdict_floor(sanitized)
    sanitized = ensure_probe_questions(sanitized)
    return sanitized, removed
