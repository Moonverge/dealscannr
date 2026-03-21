"""
Strict LLM report schema (Pydantic v2).

Implementation lives in `rag.schema.llm_report` so RAG can validate without importing the API package.
"""

from rag.schema.llm_report import ReportOutput, ReportSection

__all__ = ["ReportOutput", "ReportSection"]
