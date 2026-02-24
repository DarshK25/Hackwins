import re
from datetime import datetime, timedelta
from typing import Optional

def parse_relative_date(text: str) -> Optional[str]:
    """
    Tries to parse natural language date phrases into ISO 8601 (YYYY-MM-DD).
    Supports: 'today', 'tomorrow', 'yesterday', 'in X days', 'next week', '7 days'
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
    if "next week" in s:
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
        
    # 'in X days' or 'X days'
    match = re.search(r"in\s+(\d+)\s+days?", s) or re.search(r"(\d+)\s+days?", s)
    if match:
        days = int(match.group(1))
        return (now + timedelta(days=days)).strftime("%Y-%m-%d")
        
    # 'ten days' etc
    number_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    for word, num in number_map.items():
        if f"{word} days" in s:
            return (now + timedelta(days=num)).strftime("%Y-%m-%d")

    # If it's already ISO-like, return as is
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
        
    return None
