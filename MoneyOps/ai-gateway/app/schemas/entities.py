"""Entity schemas, enums and helper normalizers used by EntityExtractor."""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
import re
from datetime import date, timedelta


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
    gst_percent: Optional[float] = None
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
    """Return a canonical time period string for common voice phrases."""
    if not text:
        return ""
    s = text.lower().strip()
    if "today" == s or "today" in s:
        return TimePeriod.TODAY.value
    if "last 7 days" in s or "past 7 days" in s:
        return TimePeriod.LAST_7_DAYS.value
    if "last week" in s or "previous week" in s:
        return "last_week"
    if "last month" in s or "previous month" in s:
        return TimePeriod.LAST_MONTH.value
    if "this month" in s or "current month" in s:
        return "this_month"
    if "last quarter" in s or "previous quarter" in s:
        return TimePeriod.LAST_QUARTER.value
    if "this quarter" in s or "current quarter" in s:
        return "this_quarter"
    if "last year" in s or "previous year" in s:
        return TimePeriod.LAST_YEAR.value
    if "this year" in s or "current year" in s or s == "ytd" or "year to date" in s:
        return "this_year"
    # return original as fallback
    return s


def resolve_time_period_range(label: str) -> Dict[str, Optional[str]]:
    """Resolve canonical labels into concrete date ranges when possible."""
    today = date.today()
    normalized = normalize_time_period(label)

    if normalized == TimePeriod.TODAY.value:
        return {"label": normalized, "start": today.isoformat(), "end": today.isoformat()}
    if normalized == TimePeriod.LAST_7_DAYS.value:
        return {"label": normalized, "start": (today - timedelta(days=6)).isoformat(), "end": today.isoformat()}
    if normalized == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return {"label": normalized, "start": start.isoformat(), "end": end.isoformat()}
    if normalized == "this_month":
        start = today.replace(day=1)
        return {"label": normalized, "start": start.isoformat(), "end": today.isoformat()}
    if normalized == TimePeriod.LAST_MONTH.value:
        this_month_start = today.replace(day=1)
        end = this_month_start - timedelta(days=1)
        start = end.replace(day=1)
        return {"label": normalized, "start": start.isoformat(), "end": end.isoformat()}
    if normalized == "this_quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_start_month, day=1)
        return {"label": normalized, "start": start.isoformat(), "end": today.isoformat()}
    if normalized == TimePeriod.LAST_QUARTER.value:
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        this_quarter_start = today.replace(month=quarter_start_month, day=1)
        end = this_quarter_start - timedelta(days=1)
        last_quarter_start_month = ((end.month - 1) // 3) * 3 + 1
        start = end.replace(month=last_quarter_start_month, day=1)
        return {"label": normalized, "start": start.isoformat(), "end": end.isoformat()}
    if normalized == "this_year":
        start = today.replace(month=1, day=1)
        return {"label": normalized, "start": start.isoformat(), "end": today.isoformat()}
    if normalized == TimePeriod.LAST_YEAR.value:
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
        return {"label": normalized, "start": start.isoformat(), "end": end.isoformat()}

    return {"label": normalized, "start": None, "end": None}


def normalize_metric(text: str) -> str:
    if not text:
        return ""
    return text.strip().lower()


# Basic entity extraction regex patterns
ENTITY_PATTERNS: Dict[EntityType, List[str]] = {
    EntityType.AMOUNT: [
        r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
        r"\b[\d,]+(?:\.\d+)?\s*(?:lakh|crore|thousand)\b",
    ],
    EntityType.PHONE: [r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"],
    EntityType.EMAIL: [r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"],
    EntityType.GST_NUMBER: [r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b"],
    EntityType.PERCENTAGE: [r"\b\d{1,3}(?:\.\d+)?%\b"],
    # Additional types are left for LLM-based extraction
}
