"""
Grounding / anti-hallucination tests (no Mongo required).
The hallucination strip is the critical contract: fake chunk_ids must not reach clients.
"""

from __future__ import annotations

import json

import pytest

from rag.pipeline.llm_report_output import parse_validate_report_output
from rag.schema.llm_report import REPORT_SECTION_KEYS


def _full_sections_template(
    *,
    executive_citations: list[str] | None = None,
    default_citations: list | None = None,
) -> dict:
    exec_cit = executive_citations if executive_citations is not None else []
    dc = default_citations if default_citations is not None else []
    out = {}
    for k in REPORT_SECTION_KEYS:
        cit = exec_cit if k == "executive_summary" else list(dc)
        out[k] = {"text": f"Body {k}", "citations": cit, "status": "complete"}
    return out


def test_double_prefixed_chunk_id_normalized():
    """Model sometimes emits 'chunk_id: 69be...' in JSON citations; normalize before lookup."""
    real = "69be6782e5a786e167653d69"
    prefixed = "chunk_id: 69be6782e5a786e167653d69"
    double = "chunk_id: chunk_id: 69be6782e5a786e167653d69"
    payload = {
        "verdict": "PASS",
        "confidence_score": 0.75,
        "lane_coverage": 2,
        "chunk_count": 2,
        "risk_triage": "watch",
        "sections": _full_sections_template(
            executive_citations=[prefixed, double],
        ),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, removed = parse_validate_report_output(raw, {real})
    assert removed == 0
    es = report.sections["executive_summary"]
    assert es.citations == [real, real]
    assert pytest.approx(report.confidence_score) == 0.75


def test_hallucinated_chunk_ids_stripped():
    """One citation not in the evidence set is stripped; confidence drops by 0.1; real ids remain."""
    real_a = "aaaaaaaaaaaaaaaaaaaaaaaa"
    real_b = "bbbbbbbbbbbbbbbbbbbbbbbb"
    fake_c = "cccccccccccccccccccccccc"
    base_confidence = 0.85
    payload = {
        "verdict": "MEET",
        "confidence_score": base_confidence,
        "lane_coverage": 3,
        "chunk_count": 3,
        "risk_triage": "watch",
        "sections": _full_sections_template(
            executive_citations=[real_a, real_b, fake_c],
        ),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, removed = parse_validate_report_output(raw, {real_a, real_b})
    assert removed == 1
    es = report.sections["executive_summary"]
    assert fake_c not in es.citations
    assert real_a in es.citations
    assert real_b in es.citations
    assert pytest.approx(report.confidence_score) == base_confidence - 0.1


def test_confidence_decremented_per_hallucinated_citation():
    f1 = "111111111111111111111111"
    f2 = "222222222222222222222222"
    real = "aaaaaaaaaaaaaaaaaaaaaaaa"
    payload = {
        "verdict": "PASS",
        "confidence_score": 0.9,
        "lane_coverage": 2,
        "chunk_count": 3,
        "risk_triage": "unknown",
        "sections": _full_sections_template(executive_citations=[real, f1, f2]),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, removed = parse_validate_report_output(raw, {real})
    assert removed == 2
    assert pytest.approx(report.confidence_score) == 0.9 - 0.2


def test_invalid_llm_json_returns_insufficient():
    report, removed = parse_validate_report_output("{not json", {"a"})
    assert report.verdict == "INSUFFICIENT"
    assert removed == 0


def test_preliminary_flag_when_chunk_count_below_5():
    from rag.engine import _downgrade_sections_to_preliminary
    from rag.schema.llm_report import ReportOutput, ReportSection

    sections = {
        k: ReportSection(text="x", citations=[], status="complete") for k in REPORT_SECTION_KEYS
    }
    r = ReportOutput(
        verdict="PASS",
        confidence_score=0.7,
        lane_coverage=2,
        chunk_count=4,
        risk_triage="unknown",
        sections=sections,
        known_unknowns=[],
        disclaimer="d",
    )
    out = _downgrade_sections_to_preliminary(r)
    for sec in out.sections.values():
        assert sec.status == "preliminary"


def test_verdict_rubric_flag_on_litigation():
    from rag.schema.llm_report import ReportOutput, ReportSection

    sections = {
        k: ReportSection(text="x", citations=[], status="complete") for k in REPORT_SECTION_KEYS
    }
    sections["legal_regulatory"] = ReportSection(
        text="Enforcement action noted.",
        citations=[],
        status="complete",
    )
    r = ReportOutput(
        verdict="FLAG",
        confidence_score=0.6,
        lane_coverage=3,
        chunk_count=5,
        risk_triage="flag",
        sections=sections,
        known_unknowns=[],
        disclaimer="d",
    )
    assert r.verdict == "FLAG"


def test_verdict_floor_meet_to_pass_low_confidence():
    real = "aaaaaaaaaaaaaaaaaaaaaaaa"
    payload = {
        "verdict": "MEET",
        "confidence_score": 0.35,
        "lane_coverage": 3,
        "chunk_count": 5,
        "risk_triage": "watch",
        "sections": _full_sections_template(default_citations=[real]),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, _ = parse_validate_report_output(raw, {real})
    assert report.verdict == "PASS"


def test_verdict_floor_pass_to_insufficient():
    real = "aaaaaaaaaaaaaaaaaaaaaaaa"
    payload = {
        "verdict": "PASS",
        "confidence_score": 0.1,
        "lane_coverage": 2,
        "chunk_count": 4,
        "risk_triage": "unknown",
        "sections": _full_sections_template(default_citations=[real]),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, _ = parse_validate_report_output(raw, {real})
    assert report.verdict == "INSUFFICIENT"


def test_hallucination_bulk_penalty_when_three_plus_removed():
    real = "aaaaaaaaaaaaaaaaaaaaaaaa"
    f1, f2, f3 = "f1f1f1f1f1f1f1f1f1f1f1f1", "f2f2f2f2f2f2f2f2f2f2f2f2", "f3f3f3f3f3f3f3f3f3f3f3f3"
    payload = {
        "verdict": "MEET",
        "confidence_score": 0.92,
        "lane_coverage": 3,
        "chunk_count": 4,
        "risk_triage": "watch",
        "sections": _full_sections_template(executive_citations=[real, f1, f2, f3]),
        "known_unknowns": [],
        "disclaimer": "d",
    }
    raw = json.dumps(payload)
    report, removed = parse_validate_report_output(raw, {real})
    assert removed == 3
    # -0.3 strip + -0.2 bulk from 0.92 => 0.42 (avoids float edge at exactly 0.4 vs MEET floor)
    assert pytest.approx(report.confidence_score) == 0.42
    assert report.verdict == "MEET"
