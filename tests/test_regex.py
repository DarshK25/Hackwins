import re

# Test pattern matching
text = "why is my revenue down 15% this quarter?"
text_lower = text.lower()

patterns = [
    r"why.*revenue.*down",
    r"why.*\b(down|declined|drop|decrease)\b",
    r"revenue.*\b(down|dropped|declined).*\%",
]

print(f"Testing text: {text!r}")
print(f"Lowercase: {text_lower!r}\n")

for p in patterns:
    try:
        match = re.search(p, text_lower, re.IGNORECASE)
        print(f"Pattern: {p!r}")
        print(f"  Result: {'✓ MATCH' if match else '✗ NO MATCH'}")
        if match:
            print(f"  Matched: {match.group()!r}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
