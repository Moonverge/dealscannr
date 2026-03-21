from enum import Enum
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SignalCategory(str, Enum):
    TEAM = "team"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    HIRING = "hiring"
    CUSTOMER = "customer"
    FINANCIALS = "financials"
    FOUNDER = "founder"
    PRODUCT = "product"


class Signal(BaseModel):
    category: SignalCategory
    title: str
    description: str
    sentiment: Literal["positive", "negative", "neutral"]
    source: str
    date_detected: datetime | None = None
    weight: float = 0.5
