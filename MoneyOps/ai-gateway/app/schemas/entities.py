"""
Entity schemas, enums and helper normalizers used by EntityExtractor
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
import re


class EntityType(str, Enum):
    AMOUNT = "AMOUNT"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    GST_NUMBER = "GST_NUMBER"
    PERCENTAGE = "PERCENTAGE"
    CLIENT_NAME = "CLIENT_NAME"
    INVOICE_ID = "INVOICE_ID"
    METRIC = "METRIC"
    TIME_PERIOD = "TIME_PERIOD"
    PROBLEM_AREA = "PROBLEM_AREA"
    COMPETITOR_NAME = "COMPETITOR_NAME"
    TARGET_VALUE = "TARGET_VALUE"
    ENTITY_NAME = "ENTITY_NAME"  # fallback


class Entity(BaseModel):
    entity_type: EntityType
    value: Any
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    normalized_value: Optional[Any] = None
    extraction_method: Optional[str] = None


class ExtractedEntities(BaseModel):
    entities: List[Entity] = Field(default_factory=list)

    # Convenience accessors
    amount: Optional[Decimal] = None
    client_name: Optional[str] = None
    date: Optional[str] = None
    invoice_id: Optional[str] = None
    metric: Optional[str] = None
    problem_area: Optional[str] = None
    time_period: Optional[str] = None
    competitor: Optional[str] = None
    target_value: Optional[str] = None

    total_entities: int = 0
    confidence_score: float = 0.0


class MetricType(str, Enum):
    REVENUE = "revenue"
    PROFIT = "profit"
    CAC = "cac"
    LTV = "ltv"


class TimePeriod(str, Enum):
    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"


class ProblemArea(str, Enum):
    REVENUE = "revenue"
    SALES = "sales"
    COSTS = "costs"
    CASH_FLOW = "cash_flow"


class StrategyContext(BaseModel):
    business_context: Optional[Dict[str, Any]] = None
    constraints: Optional[List[str]] = None


# Simple normalizer helpers
_currency_re = re.compile(r"[₹$£,]|")
_amount_k_re = re.compile(r"(?P<num>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>k|K|m|M|l|L)\b")
_percent_re = re.compile(r"(?P<num>[0-9]+(?:\.[0-9]+)?)\s*%")


def normalize_amount(text: str) -> Decimal:
    """Normalize amount strings to Decimal. Handles 50,000, 50k, ₹50k, 10L, 1.2m"""
    if text is None:
        raise ValueError("No amount to normalize")
    s = str(text).strip()
    # strip currency symbols and commas
    s = re.sub(r"[₹$£,]", "", s)

    # handle percentage like values - caller should use percentage normalizer
    m = _amount_k_re.search(s)
    if m:
        num = Decimal(m.group("num"))
        unit = m.group("unit").lower()
        if unit == "k":
            return num * Decimal(1000)
        if unit == "l":
            return num * Decimal(100000)
        if unit == "m":
            return num * Decimal(1000000)

    # remove non numeric characters
    s = re.sub(r"[^0-9\.\-]", "", s)
    if s == "":
        raise ValueError(f"Unable to parse amount from '{text}'")
    return Decimal(s)


def normalize_time_period(text: str) -> str:
    """Return a canonical time period string for simple phrases. Not exhaustive."""
    if not text:
        return ""
    s = text.lower().strip()
    if "last month" in s or "previous month" in s:
        return TimePeriod.LAST_MONTH.value
    if "last quarter" in s or "previous quarter" in s:
        return TimePeriod.LAST_QUARTER.value
    if "last year" in s or "previous year" in s:
        return TimePeriod.LAST_YEAR.value
    if "today" in s or "today" == s:
        return TimePeriod.TODAY.value
    # return original as fallback
    return s


def normalize_metric(text: str) -> str:
    if not text:
        return ""
    return text.strip().lower()


# Basic entity extraction regex patterns
ENTITY_PATTERNS: Dict[EntityType, List[str]] = {
    EntityType.AMOUNT: [r"(?:₹|Rs\.?|INR)?\s*\d{1,3}(?:[,\d]{0,})?(?:\.\d+)?\s*(?:k|K|m|M|l|L)?"],
    EntityType.PHONE: [r"\b\+?\d[\d\-\s]{7,}\b"],
    EntityType.EMAIL: [r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"],
    EntityType.GST_NUMBER: [r"\b[0-9A-Z]{15}\b"],
    EntityType.PERCENTAGE: [r"\b\d{1,3}(?:\.\d+)?%\b"],
    # Additional types are left for LLM-based extraction
}
