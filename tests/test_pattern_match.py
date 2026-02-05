"""Test pattern matching directly"""
import asyncio
import re
from typing import Optional, Dict, Any
from enum import Enum

class Intent(str, Enum):
    PROBLEM_DIAGNOSIS = "PROBLEM_DIAGNOSIS"
    BUSINESS_HEALTH_CHECK = "BUSINESS_HEALTH_CHECK"
    INVOICE_CREATE = "INVOICE_CREATE"

def _build_intent_patterns() -> Dict[Intent, list]:
    """Build regex patterns for fast intent classification"""
    return {
        Intent.PROBLEM_DIAGNOSIS: [
            r"why.*revenue.*down",
            r"why.*sales.*down",
            r"why.*\b(down|declined|drop|decrease)\b",
            r"\b(why|what).*wrong",
            r"\b(why|reason).*declining",
            r"\b(reason|cause).*drop",
            r"revenue.*\b(down|dropped|declined).*\%",
            r"sales.*\b(down|dropped|declined).*\%",
        ],
        Intent.BUSINESS_HEALTH_CHECK: [
            r"how.*business.*\b(doing|health|performing)",
            r"business.*\b(health|status|score|performance)",
            r"\b(health|performance).*score",
            r"\b(overall|general).*\b(health|performance|status)",
            r"check.*business",
        ],
    }

def _pattern_classify(user_input: str, patterns: Dict[Intent, list]) -> Optional[Dict[str, Any]]:
    """Fast pattern-based classification; returns dict or None"""
    user_input_lower = (user_input or "").lower().strip()
    print(f"Input (lowercase): {user_input_lower!r}")

    for intent, pattern_list in patterns.items():
        for pattern in pattern_list:
            try:
                if re.search(pattern, user_input_lower, re.IGNORECASE):
                    confidence = 0.95 if len(pattern) > 20 else 0.9 if len(pattern) > 15 else 0.85
                    print(f"✓ MATCH: Intent={intent.value}, Pattern={pattern!r}, Confidence={confidence}")
                    return {"intent": intent, "confidence": confidence, "pattern": pattern}
            except Exception as e:
                print(f"✗ Error in pattern {pattern!r}: {e}")
                continue

    return None

# Test
if __name__ == "__main__":
    patterns = _build_intent_patterns()
    
    test_cases = [
        "Why is my revenue down 15% this quarter?",
        "How is my business health?",
        "Create invoice for Acme",
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test!r}")
        print('='*60)
        result = _pattern_classify(test, patterns)
        if result:
            print(f"Result: {result}")
        else:
            print("No pattern match found")
