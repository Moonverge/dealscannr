from datetime import datetime

from rag.engine import RAGEngine
from rag.pipeline.query_parser import parse_query
from rag.schema import IntelligenceReport
from rag.schema.llm_report import ReportOutput
from rag.utils.display import format_company_display_name

from config.settings import settings


def _report_output_to_intelligence(report: ReportOutput, company_name: str) -> IntelligenceReport:
    exec_sec = report.sections.get("executive_summary")
    summary = exec_sec.text if exec_sec else ""
    vmap = {"MEET": "green", "PASS": "yellow", "FLAG": "red", "INSUFFICIENT": "yellow"}
    verdict = vmap.get(report.verdict, "yellow")
    return IntelligenceReport(
        company_name=company_name,
        generated_at=datetime.utcnow(),
        verdict=verdict,  # type: ignore[arg-type] — legacy UI uses green/yellow/red
        confidence=float(report.confidence_score),
        summary=summary[:2000],
        signals=[],
        sources_used=[],
        raw_chunks_count=report.chunk_count,
    )


def run_search(query: str) -> IntelligenceReport:
    engine = RAGEngine(
        groq_api_key=settings.groq_api_key,
        qdrant_url=settings.qdrant_url,
        openai_api_key=settings.openai_api_key,
        together_api_key=settings.together_api_key,
        nomic_api_key=settings.nomic_api_key,
        firecrawl_api_key=settings.firecrawl_api_key,
        llm_provider=settings.llm_provider,
    )
    report, _hallucinated, _usage = engine.run(query)
    parsed = parse_query(query)
    display_name = format_company_display_name(
        parsed.entity or (query or "").strip()[:200] or "Unknown Company",
    )
    return _report_output_to_intelligence(report, display_name)
