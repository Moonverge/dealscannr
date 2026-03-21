"""API-facing models; shared report schema is defined in rag.schema.llm_report."""

from .report import ReportOutput, ReportSection

__all__ = ["ReportOutput", "ReportSection"]
