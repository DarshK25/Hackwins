"""Date resolution helpers for already-extracted relative date phrases."""
import re
from datetime import datetime, timedelta, date
from typing import Optional


def parse_relative_date(text: str) -> Optional[str]:
    """Resolve a relative date phrase into ISO 8601.

    This is intentionally strict. It should be used after the LLM or another
    higher-level parser has already isolated the date phrase, not on arbitrary
    raw user input like "next week's invoices".
    """
    if not text:
        return None

    s = re.sub(r"\s+", " ", text.lower().strip().replace("-", " "))
    now = datetime.now()

    if re.fullmatch(r"today", s):
        return now.strftime("%Y-%m-%d")
    if re.fullmatch(r"tomorrow", s):
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if re.fullmatch(r"yesterday", s):
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if re.fullmatch(r"next ?week", s):
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
    if re.fullmatch(r"next month|a month|one month", s):
        return (now + timedelta(days=30)).strftime("%Y-%m-%d")
    if re.fullmatch(r"end of (this )?month", s):
        first_of_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_of_next - timedelta(days=1)
        return end_of_month.strftime("%Y-%m-%d")

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    weekday_match = re.fullmatch(r"(?:next )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", s)
    if weekday_match:
        day_name = weekday_match.group(1)
        day_num = weekdays[day_name]
        current_weekday = now.weekday()
        days_ahead = day_num - current_weekday
        if days_ahead <= 0:
            days_ahead += 7
        if s.startswith("next ") and days_ahead < 7:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    match = re.fullmatch(r"(?:in )?(\d+)\s+days?", s)
    if match:
        days = int(match.group(1))
        return (now + timedelta(days=days)).strftime("%Y-%m-%d")

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
        if s in {f"{word} day", f"{word} days", f"in {word} day", f"in {word} days"}:
            return (now + timedelta(days=num)).strftime("%Y-%m-%d")

    if s in {"a couple of weeks", "couple of weeks"}:
        return (now + timedelta(days=14)).strftime("%Y-%m-%d")
    if s in {"a few days", "few days"}:
        return (now + timedelta(days=3)).strftime("%Y-%m-%d")

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
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
