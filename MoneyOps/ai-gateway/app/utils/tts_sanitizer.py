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

    sanitized = re.sub(
        r"\[\s*(\d{4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\]",
        lambda m: _format_date_parts(m.group(1), m.group(2), m.group(3)),
        sanitized,
    )
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
    sanitized = sanitized.replace("$", "rupees ")
    sanitized = sanitized.replace("%", " percent")

    sanitized = _format_currency_mentions_for_speech(sanitized)
    sanitized = _format_indian_numbers_for_speech(sanitized)
    sanitized = re.sub(r"\b([A-Z]{1,4})-(\d{4})-(\d{3,})\b", r"\1-\2-\3", sanitized)
    sanitized = re.sub(r"\b(\d+(?:\.\d+)?)\s+lakh\.00\b", r"\1 lakh", sanitized)
    sanitized = re.sub(r"\b(\d+(?:\.\d+)?)\s+crore\.00\b", r"\1 crore", sanitized)
    sanitized = re.sub(r"\b(\d+(?:\.\d+)?)\s+thousand\.00\b", r"\1 thousand", sanitized)
    sanitized = sanitized.replace(".00", "")
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


def _format_date_parts(year: str, month: str, day: str) -> str:
    month_names = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }
    try:
        month_num = int(month)
        day_num = int(day)
        year_num = int(year)
    except ValueError:
        return f"{year}-{month}-{day}"
    month_name = month_names.get(month_num)
    if not month_name:
        return f"{year}-{month}-{day}"
    return f"{month_name} {day_num}, {year_num}"


def _format_currency_mentions_for_speech(text: str) -> str:
    def convert_lakh_crore(match: re.Match[str]) -> str:
        value = match.group(1)
        unit = match.group(2).lower()
        return f"{value} {unit} rupees"

    def convert_plain(match: re.Match[str]) -> str:
        raw = match.group(1).replace(",", "")
        try:
            amount = float(raw)
        except ValueError:
            return match.group(0)

        if amount.is_integer():
            amount = int(amount)
            if 1900 <= amount <= 2099:
                return str(amount)

        spoken = _format_numeric_amount(amount)
        return f"{spoken} rupees"

    converted = re.sub(
        r"\b(?:INR|Rs\.?)\s*([\d.]+)\s*(lakh|crore)\b",
        convert_lakh_crore,
        text,
        flags=re.IGNORECASE,
    )
    converted = re.sub(
        r"\brupees\s+([\d.]+)\s*(lakh|crore)\b",
        convert_lakh_crore,
        converted,
        flags=re.IGNORECASE,
    )
    converted = re.sub(
        r"\b(?:INR|Rs\.?|rupees)\s*([\d,]+(?:\.\d+)?)\b",
        convert_plain,
        converted,
        flags=re.IGNORECASE,
    )
    return converted


def _format_numeric_amount(amount: float) -> str:
    if amount >= 10_000_000:
        value = amount / 10_000_000
        return f"{value:.1f} crore".replace(".0 ", " ")
    if amount >= 100_000:
        value = amount / 100_000
        return f"{value:.1f} lakh".replace(".0 ", " ")
    if amount >= 1_000:
        value = amount / 1_000
        return f"{value:.1f} thousand".replace(".0 ", " ")
    if float(amount).is_integer():
        return str(int(amount))
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def _format_indian_numbers_for_speech(text: str) -> str:
    """Convert large numeric strings into a more natural Indian speech format."""

    def convert(match: re.Match[str]) -> str:
        raw = match.group(0)
        digits = raw.replace(",", "")
        try:
            number = int(digits)
        except ValueError:
            return raw

        if 1900 <= number <= 2099:
            return digits

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

    return re.sub(r"(?<![A-Za-z-])\b[\d,]{4,}\b(?!-[A-Za-z0-9])", convert, text)
