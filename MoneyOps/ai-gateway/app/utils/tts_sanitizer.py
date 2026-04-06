import re


_LEAKED_IDENTIFIER_PATTERN = re.compile(
    r"\b("
    r"get_financial_summary|create_client|get_invoices|get_clients|"
    r"search_market|search_market_intelligence|get_business_health|"
    r"get_business_health_score|record_payment|create_invoice|"
    r"record_transaction|mark_invoice_paid|check_compliance|remember|recall"
    r")\b",
    re.IGNORECASE,
)


def sanitize_for_tts(text: str) -> str:
    """Convert model output into speech-safe plain language."""
    if not text:
        return ""

    sanitized = text

    sanitized = _LEAKED_IDENTIFIER_PATTERN.sub("", sanitized)
    sanitized = re.sub(r"\*\*(.+?)\*\*", r"\1", sanitized)
    sanitized = re.sub(r"\*(.+?)\*", r"\1", sanitized)
    sanitized = re.sub(r"`([^`]+)`", r"\1", sanitized)
    sanitized = re.sub(r"^#{1,6}\s*", "", sanitized, flags=re.MULTILINE)
    sanitized = sanitized.replace("|", ", ")
    sanitized = sanitized.replace("_", " ")

    sanitized = re.sub(r"\s*=\s*", " is ", sanitized)
    sanitized = re.sub(r"\s*/\s*", " out of ", sanitized)
    sanitized = sanitized.replace("₹", "rupees ")
    sanitized = sanitized.replace("$", "dollars ")
    sanitized = sanitized.replace("%", " percent")

    sanitized = _format_indian_numbers_for_speech(sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def _format_indian_numbers_for_speech(text: str) -> str:
    """Convert large numeric strings into a more natural Indian speech format."""

    def convert(match: re.Match[str]) -> str:
        raw = match.group(0)
        digits = raw.replace(",", "")
        try:
            number = int(digits)
        except ValueError:
            return raw

        if number >= 10_000_000:
            crores = number / 10_000_000
            return f"{crores:.1f} crore".replace(".0 ", " ")
        if number >= 100_000:
            lakhs = number / 100_000
            return f"{lakhs:.1f} lakh".replace(".0 ", " ")
        if number >= 1_000:
            thousands = number / 1_000
            if thousands.is_integer():
                return f"{int(thousands)} thousand"
            return f"{thousands:.1f} thousand".replace(".0 ", " ")
        return digits

    return re.sub(r"\b[\d,]{4,}\b", convert, text)
