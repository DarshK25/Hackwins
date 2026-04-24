"""
Date parser for natural language date phrases.

Supports:
- relative phrases such as "tomorrow", "in 10 days", "next friday"
- month/day phrases such as "fifth march", "march 5", "5th of march"
- ISO date passthrough
"""
import re
from datetime import date, datetime, timedelta
from typing import Optional


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DAY_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
    "twenty first": 21, "twenty second": 22, "twenty third": 23, "twenty fourth": 24,
    "twenty fifth": 25, "twenty sixth": 26, "twenty seventh": 27, "twenty eighth": 28,
    "twenty ninth": 29, "thirtieth": 30, "thirty first": 31,
}


def _sanitize(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = cleaned.replace(",", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _parse_day_token(token: str) -> Optional[int]:
    token = token.strip()
    if not token:
        return None

    if token.isdigit():
        day = int(token)
        return day if 1 <= day <= 31 else None

    ordinal_match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)", token)
    if ordinal_match:
        day = int(ordinal_match.group(1))
        return day if 1 <= day <= 31 else None

    return DAY_WORDS.get(token)


def _format_candidate_date(year: int, month: int, day: int, today: date, prefer_future: bool) -> Optional[str]:
    try:
        candidate = date(year, month, day)
    except ValueError:
        return None

    if prefer_future and candidate < today:
        try:
            candidate = date(year + 1, month, day)
        except ValueError:
            return None

    return candidate.isoformat()


def _parse_month_day_phrase(text: str, today: date, prefer_future: bool) -> Optional[str]:
    patterns = [
        r"\b(?P<day>\d{1,2}(?:st|nd|rd|th)?|[a-z]+(?: [a-z]+)?)\s+(?:of\s+)?(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+(?P<year>\d{4}))?\b",
        r"\b(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(?P<day>\d{1,2}(?:st|nd|rd|th)?|[a-z]+(?: [a-z]+)?)(?:\s+(?P<year>\d{4}))?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        month_token = match.group("month")
        day_token = match.group("day")
        year_token = match.group("year")

        month = MONTH_MAP.get(month_token)
        day = _parse_day_token(day_token)
        if not month or not day:
            continue

        year = int(year_token) if year_token else today.year
        parsed = _format_candidate_date(
            year=year,
            month=month,
            day=day,
            today=today,
            prefer_future=prefer_future and not year_token,
        )
        if parsed:
            return parsed

    return None


def parse_relative_date(text: str, prefer_future: bool = False) -> Optional[str]:
    """
    Tries to parse natural language date phrases into ISO 8601 (YYYY-MM-DD).

    `prefer_future=True` is useful for due dates where a yearless month/day phrase
    like "fifth march" should resolve to the next future occurrence.
    """
    if not text:
        return None

    raw = text.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw[:10]

    s = _sanitize(text)
    now = datetime.now()
    today = now.date()

    if "today" in s:
        return now.strftime("%Y-%m-%d")
    if "tomorrow" in s:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if "yesterday" in s:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "next week" in s or "nextweek" in s:
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
    if "next month" in s:
        return (now + timedelta(days=30)).strftime("%Y-%m-%d")
    if "end of month" in s:
        first_of_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_of_month = first_of_next - timedelta(days=1)
        return end_of_month.strftime("%Y-%m-%d")

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    for day_name, day_num in weekdays.items():
        if day_name in s:
            current_weekday = now.weekday()
            days_ahead = day_num - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            if "next" in s and days_ahead < 7:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    match = re.search(r"in\s+(\d+)\s+days?", s) or re.search(r"(\d+)\s+days?", s)
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
        if f"{word} days" in s or f"{word}days" in s:
            return (now + timedelta(days=num)).strftime("%Y-%m-%d")

    next_days_match = re.search(r"(\d+)\s*(?:next)?\s*days?", s)
    if not match and next_days_match:
        days = int(next_days_match.group(1))
        if 1 <= days <= 365:
            return (now + timedelta(days=days)).strftime("%Y-%m-%d")

    month_day = _parse_month_day_phrase(s, today=today, prefer_future=prefer_future)
    if month_day:
        return month_day

    return None


def is_date_fragment(text: str) -> bool:
    """
    Returns True if the text looks like a date/time fragment rather than an amount.
    Helps prevent date phrases from being parsed as monetary amounts.
    """
    indicators = [
        "days", "next", "week", "month", "friday", "monday", "tuesday",
        "wednesday", "thursday", "saturday", "sunday", "tomorrow", "today",
        "january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
        "oct", "nov", "dec",
    ]
    text_lower = text.lower()
    return any(ind in text_lower for ind in indicators)
