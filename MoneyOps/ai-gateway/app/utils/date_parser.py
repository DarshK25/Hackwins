"""
Date parser for natural language date phrases.
Enhanced for:
- "next friday", "next monday", etc. (named weekdays)  
- "nineteen", "ten nine" etc. multi-word date fragments (NOT amounts)
- ISO date passthrough
"""
import re
from datetime import datetime, timedelta, date
from typing import Optional


def parse_relative_date(text: str) -> Optional[str]:
    """
    Tries to parse natural language date phrases into ISO 8601 (YYYY-MM-DD).
    Supports: 'today', 'tomorrow', 'yesterday', 'in X days', 'next week',
              'next friday', '7 days', 'nineteen days', 'ten nine' etc.
    Returns ISO string or None.
    """
    if not text:
        return None

    s = text.lower().strip()
    now = datetime.now()

    # Simple fixed phrases
    if "today" in s:
        return now.strftime("%Y-%m-%d")
    if "tomorrow" in s:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "yesterday" in s:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "next week" in s or "nextweek" in s:
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
    if "next month" in s:
        # Approx: 30 days
        return (now + timedelta(days=30)).strftime("%Y-%m-%d")
    if "end of month" in s:
        # Last day of current month
        first_of_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_of_next - timedelta(days=1)
        return end_of_month.strftime("%Y-%m-%d")

    # Named weekdays: "next friday", "next monday" etc.
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    for day_name, day_num in weekdays.items():
        if day_name in s:
            current_weekday = now.weekday()
            days_ahead = day_num - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            # If "next" is mentioned and target is still in this week, add another week
            if "next" in s and days_ahead < 7:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # 'in X days' or 'X days'
    match = re.search(r"in\s+(\d+)\s+days?", s) or re.search(r"(\d+)\s+days?", s)
    if match:
        days = int(match.group(1))
        return (now + timedelta(days=days)).strftime("%Y-%m-%d")

    # Word-based numbers (expanded to cover STT outputs like "ten nine", "nineteen")
    # Extended number map including teens and twenties
    number_map = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "twenty one": 21, "twenty two": 22, "twenty three": 23, "twenty four": 24,
        "twenty five": 25, "twenty six": 26, "twenty seven": 27, "twenty eight": 28,
        "twenty nine": 29, "thirty": 30,
    }
    for word, num in number_map.items():
        if f"{word} days" in s or f"{word}days" in s:
            return (now + timedelta(days=num)).strftime("%Y-%m-%d")

    # Support "X next days" (STT artifact: "ten nine next days" → parse digit-day sequences)
    # Pattern: digit(s) followed by "next days" or similar
    next_days_match = re.search(r"(\d+)\s*(?:next)?\s*days?", s)
    if not match and next_days_match:
        days = int(next_days_match.group(1))
        if 1 <= days <= 365:
            return (now + timedelta(days=days)).strftime("%Y-%m-%d")

    # If it's already ISO-like, return as is
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]

    return None


def is_date_fragment(text: str) -> bool:
    """
    Returns True if the text looks like a date/time fragment rather than an amount.
    Helps prevent "ten nine next days" from being parsed as a monetary amount.
    """
    indicators = ["days", "next", "week", "month", "friday", "monday", "tuesday",
                  "wednesday", "thursday", "saturday", "sunday", "tomorrow", "today"]
    text_lower = text.lower()
    return any(ind in text_lower for ind in indicators)
