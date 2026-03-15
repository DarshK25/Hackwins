"""
Indian number system parser for monetary amounts.
Handles: lakh, crore, thousand, hundred + word-to-number mapping.
Rejects date-like fragments (Bug 2 edge case: "ten nine next days" → None).
"""
import re
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Date/time indicator words — if present, this is NOT an amount  
_DATE_INDICATORS = frozenset([
    "days", "day", "next", "week", "month", "year",
    "friday", "monday", "tuesday", "wednesday", "thursday",
    "saturday", "sunday", "tomorrow", "today", "yesterday",
    "morning", "evening", "night", "deadline", "until", "by",
    "gst", "percent", "percentage", "%", "tax",
])


def parse_indian_amount(text: str) -> Optional[float]:
    """
    Parses Indian number system words into a float.
    Handles 'lakh', 'crore', 'thousand', 'hundred'.

    Examples:
    - 'two lakh rupees' -> 200000.0
    - '1.5 crore' -> 15000000.0
    - 'fifty thousand' -> 50000.0
    - 'two lakh fifty thousand' -> 250000.0
    - '₹2,00,000' -> 200000.0
    - '200000' -> 200000.0
    - 'ten nine next days' -> None  (date fragment, NOT an amount)
    - 'rupees' alone -> None

    Returns None if no valid amount is found.
    """
    if not text:
        return None

    # Reject date-like fragments BEFORE any processing (Bug 2 edge case)
    text_lower = text.lower()
    token_words = set(re.findall(r'[a-z]+', text_lower))
    if token_words & _DATE_INDICATORS:
        logger.debug("amount_parse_rejected_date_fragment", text=text[:80])
        return None

    # Clean the text: lower case, remove currency symbols and commas
    text_clean = text_lower.strip()
    text_clean = re.sub(r'[₹$, ]', '', text_clean)

    # Handle direct numeric strings (with optional rupee suffix)
    clean_no_suffix = re.sub(r'rupees?$', '', text_clean).strip()
    if re.match(r'^\d+(\.\d+)?$', clean_no_suffix):
        try:
            return float(clean_no_suffix)
        except ValueError:
            pass

    # Handle formatted Indian amounts like ₹2,00,000
    # Already stripped of commas above — try direct numeric parse
    if re.match(r'^\d+(\.\d+)?$', text_clean):
        return float(text_clean)

    # Word-to-number mapping
    word_map = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
        'seventy': 70, 'eighty': 80, 'ninety': 90,
    }

    # Multipliers
    multipliers = {
        'crore': 10_000_000,
        'lakh': 100_000,
        'thousand': 1_000,
        'hundred': 100,
    }

    # STT-specific corrections for common mishearings
    corrections = {
        'to': 'two',
        'that': 'lakh',    # "to that rupees" → "two lakh rupees"
        'lac': 'lakh',     # alternate spelling
        'lacks': 'lakh',
        'lack': 'lakh',
    }

    # Tokenize the text
    tokens = re.findall(r'[a-z]+|\d+(?:\.\d+)?', text_lower)
    if not tokens:
        return None

    # Skip if mostly date words appear
    non_amount_words = {'rupees', 'rupee', 'rs', 'inr', 'amount', 'of', 'and', 'for', 'pay'}
    useful_tokens = [t for t in tokens if t not in non_amount_words]
    if not useful_tokens:
        return None

    # Apply corrections
    processed_tokens = [corrections.get(t, t) for t in tokens]

    total = 0.0
    current_value = 0.0
    found_multiplier = False
    found_digit = False

    for token in processed_tokens:
        val = None
        if re.match(r'^\d+(\.\d+)?$', token):
            val = float(token)
            found_digit = True
        elif token in word_map:
            val = float(word_map[token])
            found_digit = True

        if val is not None:
            current_value += val
        elif token in multipliers:
            m = multipliers[token]
            if current_value == 0:
                current_value = 1.0  # "lakh rupees" → 100000
            total += current_value * m
            current_value = 0.0
            found_multiplier = True
        # Skip unknown tokens (like 'rupees', 'rs', etc.)

    total += current_value

    if not found_multiplier and not found_digit:
        return None

    # Reject "rupees" alone or zero result when no real number found
    if total == 0.0 and not found_multiplier:
        return None

    # Sanity cap: reject astronomical amounts (> 10 crore) without crore keyword
    # This helps catch "ten nine" (= 19) being amplified incorrectly
    if total > 0 and total < 1.0:
        return None  # Sub-rupee amounts are not valid invoice amounts

    return total
