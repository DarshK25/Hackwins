"""
Indian number system parser for monetary amounts.
Handles lakh, crore, thousand, hundred and common STT mishearings.
Rejects date-like fragments so phrases such as "ten nine next days" are not
misread as money.
"""
import re
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

_DATE_INDICATORS = frozenset([
    "days", "day", "next", "week", "month", "year",
    "friday", "monday", "tuesday", "wednesday", "thursday",
    "saturday", "sunday", "tomorrow", "today", "yesterday",
    "morning", "evening", "night", "deadline", "until", "by",
    "gst", "percent", "percentage", "%", "tax",
])


def parse_indian_amount(text: str) -> Optional[float]:
    """
    Parse Indian-style monetary expressions into a float.

    Examples:
    - "two lakh rupees" -> 200000.0
    - "1.5 crore" -> 15000000.0
    - "fifty thousand" -> 50000.0
    - "to lakh" -> 200000.0
    - "ten nine next days" -> None
    """
    if not text:
        return None

    text_lower = text.lower()
    token_words = set(re.findall(r"[a-z]+", text_lower))
    if token_words & _DATE_INDICATORS:
        logger.debug("amount_parse_rejected_date_fragment", text=text[:80])
        return None

    text_clean = text_lower.strip()
    text_clean = re.sub(r"[₹$, ]", "", text_clean)

    clean_no_suffix = re.sub(r"rupees?$", "", text_clean).strip()
    if re.match(r"^\d+(\.\d+)?$", clean_no_suffix):
        try:
            return float(clean_no_suffix)
        except ValueError:
            pass

    if re.match(r"^\d+(\.\d+)?$", text_clean):
        return float(text_clean)

    word_map = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90,
    }

    multipliers = {
        "crore": 10_000_000,
        "lakh": 100_000,
        "thousand": 1_000,
        "hundred": 100,
    }

    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text_lower)
    if not tokens:
        return None

    non_amount_words = {"rupees", "rupee", "rs", "inr", "amount", "of", "and", "for", "pay"}
    useful_tokens = [t for t in tokens if t not in non_amount_words]
    if not useful_tokens:
        return None

    def _is_numeric_like(token: str) -> bool:
        return bool(re.match(r"^\d+(\.\d+)?$", token)) or token in word_map

    amount_units = set(multipliers) | {"rupee", "rupees", "rs", "inr"}

    processed_tokens = []
    for idx, token in enumerate(tokens):
        prev_token = tokens[idx - 1] if idx > 0 else ""
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else ""

        if token in {"lac", "lacks", "lack"}:
            processed_tokens.append("lakh")
        elif token == "to" and next_token in amount_units:
            # Preserve the helpful STT correction for "to lakh" but avoid
            # turning plain phrases like "to collect" into the number 2.
            processed_tokens.append("two")
        elif token == "that" and _is_numeric_like(prev_token):
            processed_tokens.append("lakh")
        else:
            processed_tokens.append(token)

    total = 0.0
    current_value = 0.0
    found_multiplier = False
    found_digit = False

    for token in processed_tokens:
        val = None
        if re.match(r"^\d+(\.\d+)?$", token):
            val = float(token)
            found_digit = True
        elif token in word_map:
            val = float(word_map[token])
            found_digit = True

        if val is not None:
            current_value += val
        elif token in multipliers:
            multiplier = multipliers[token]
            if current_value == 0:
                current_value = 1.0
            total += current_value * multiplier
            current_value = 0.0
            found_multiplier = True

    total += current_value

    if not found_multiplier and not found_digit:
        return None

    if total == 0.0 and not found_multiplier:
        return None

    if total > 0 and total < 1.0:
        return None

    return total
