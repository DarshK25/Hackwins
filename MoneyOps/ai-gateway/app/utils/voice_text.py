import re
from datetime import date
from typing import Iterable, Optional


DEFAULT_TOOL_NAMES = (
    "get_financial_summary",
    "get_revenue_breakdown",
    "get_invoice_aging",
    "get_invoices",
    "get_invoice_details",
    "create_invoice",
    "update_invoice_status",
    "get_client_profile",
    "get_clients",
    "create_client",
    "update_client",
    "record_payment",
    "reconcile_payment",
    "get_payment_history",
    "record_expense",
    "get_expense_analysis",
    "bulk_categorize_expenses",
    "get_cash_flow_forecast",
    "get_business_health_score",
    "check_compliance",
    "compute_gst_liability",
    "get_tds_reconciliation",
    "search_market_intelligence",
    "send_collection_reminder",
    "send_invoice_email",
    "get_daily_briefing",
    "set_reminder",
    "generate_invoice_pdf",
    "get_ledger_statement",
    "get_profitability_by_client",
    "get_overdue_action_plan",
    "run_client_360_assessment",
    "run_daily_brief",
    "detect_churn_risks",
    "find_growth_opportunities",
    "run_pricing_intelligence",
)


def format_inr_words(amount: float) -> str:
    if not amount:
        return "zero"
    n = int(abs(amount))
    prefix = "minus " if amount < 0 else ""
    parts = []
    if n >= 10_000_000:
        crore = n // 10_000_000
        parts.append(f"{crore} crore")
        n %= 10_000_000
    if n >= 100_000:
        lakh = n // 100_000
        parts.append(f"{lakh} lakh")
        n %= 100_000
    if n >= 1_000:
        thousand = n // 1_000
        parts.append(f"{thousand} thousand")
        n %= 1_000
    if n > 0:
        parts.append(str(n))
    return prefix + (" ".join(parts) if parts else "zero")


def _format_date_for_speech(value: str) -> str:
    if not value:
        return ""

    array_match = re.search(r"\[[\d\s,thousand]+\]", value, re.IGNORECASE)
    if array_match:
        raw_parts = [part.strip() for part in array_match.group(0).strip("[]").split(",")]
        nums = []
        for raw in raw_parts:
            if "thousand" in raw.lower():
                number = re.search(r"\d+", raw)
                nums.append(int(number.group(0)) * 1000 if number else 0)
            else:
                try:
                    nums.append(int(raw))
                except ValueError:
                    nums.append(0)
        if len(nums) >= 3:
            try:
                return date(nums[0], nums[1], nums[2]).strftime("%B %d, %Y").replace(" 0", " ")
            except Exception:
                pass

    try:
        return date.fromisoformat(value.strip()[:10]).strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return value


def sanitize_for_tts(text: str, tool_names: Optional[Iterable[str]] = None) -> str:
    if not text or not text.strip():
        return ""

    sanitized = text
    tool_names = tuple(tool_names or DEFAULT_TOOL_NAMES)

    for tool_name in tool_names:
        sanitized = re.sub(rf"\b{re.escape(tool_name)}\b", "", sanitized)

    sanitized = re.sub(
        r"\[\s*(?:\d+\s*(?:thousand)?\s*,\s*){2}\d+\s*\]",
        lambda match: _format_date_for_speech(match.group(0)),
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"\b20\d{2}-\d{2}-\d{2}\b",
        lambda match: _format_date_for_speech(match.group(0)),
        sanitized,
    )

    def replace_inr_scaled(match: re.Match) -> str:
        number = float(match.group(1))
        unit = match.group(2).lower()
        absolute = round(number * (100_000 if unit == "lakh" else 10_000_000))
        return f"{format_inr_words(absolute)} rupees"

    sanitized = re.sub(
        r"(?:INR|Rs\.?|₹)\s*([\d.]+)\s*(lakh|crore)\b",
        replace_inr_scaled,
        sanitized,
        flags=re.IGNORECASE,
    )

    def replace_currency(match: re.Match) -> str:
        raw = match.group(1).replace(",", "").split(".")[0]
        try:
            value = int(raw)
        except ValueError:
            return match.group(0)
        if 1900 <= value <= 2099:
            return str(value)
        return f"{format_inr_words(value)} rupees"

    sanitized = re.sub(r"(?:₹|Rs\.?|INR|\$)\s*([\d,.]+)", replace_currency, sanitized, flags=re.IGNORECASE)

    def replace_large_number(match: re.Match) -> str:
        value = int(match.group(0).replace(",", ""))
        if 1900 <= value <= 2099:
            return str(value)
        if value < 10_000:
            return match.group(0)
        return format_inr_words(value)

    sanitized = re.sub(
        r"(?<![A-Za-z0-9-])\b\d{5,}(?:,\d{3})*\b(?!-[A-Za-z0-9])",
        replace_large_number,
        sanitized,
    )

    sanitized = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", sanitized)
    sanitized = re.sub(r"\*\*(.+?)\*\*", r"\1", sanitized)
    sanitized = re.sub(r"\*(.+?)\*", r"\1", sanitized)
    sanitized = re.sub(r"`(.+?)`", r"\1", sanitized)
    sanitized = re.sub(r"#{1,6}\s+", "", sanitized)
    sanitized = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", sanitized)

    lines = sanitized.splitlines()
    spoken_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") or stripped.startswith("• "):
            stripped = stripped[2:].strip()
        else:
            stripped = re.sub(r"^\d+\.\s+", "", stripped)
        spoken_lines.append(stripped)
    sanitized = ". ".join(spoken_lines)

    sanitized = sanitized.replace("=", " is ")
    sanitized = sanitized.replace("|", ", ")
    sanitized = sanitized.replace("_", " ")
    sanitized = sanitized.replace("\\", " ")
    sanitized = sanitized.replace("<", "")
    sanitized = sanitized.replace(">", "")
    sanitized = re.sub(r"\.00\b", "", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    sanitized = re.sub(r"\.\s*\.+", ".", sanitized)

    words = sanitized.split()
    if len(words) > 90:
        candidate = " ".join(words[:90])
        sentence_endings = [candidate.rfind("."), candidate.rfind("!"), candidate.rfind("?")]
        sentence_end = max(sentence_endings)
        if sentence_end > 0:
            sanitized = candidate[: sentence_end + 1]
        else:
            sanitized = candidate.rstrip(",;:") + "."

    return sanitized.strip()
