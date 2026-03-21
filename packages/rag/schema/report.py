from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .signal import Signal


class IntelligenceReport(BaseModel):
    company_name: str
    generated_at: datetime
    verdict: Literal["green", "yellow", "red"]
    confidence: float
    summary: str
    signals: list[Signal]
    sources_used: list[str]
    raw_chunks_count: int = 0
