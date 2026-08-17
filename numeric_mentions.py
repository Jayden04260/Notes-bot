"""
numeric_mentions.py

Lightweight, local, regex-based extraction of money amounts and
percentages mentioned on the call, for a "Numbers Mentioned" table. No
LLM/API call - just pattern matching, so it's cheap and easy to unit test.

Deliberately skips plain standalone integers (page numbers, "the 3rd
point", counts) - without much heavier NLP those are mostly noise, so
this sticks to money/percentages, which are unambiguous.
"""

import re

_MONEY_RE = re.compile(
    r"[$£€]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|m|bn|million|billion|thousand))?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:dollars?|usd|pounds?|gbp|euros?|eur)\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s?(?:%|percent\b)", re.IGNORECASE)


def find_numbers(lines: list[tuple[str, str]]) -> list[tuple[str, str, str, str]]:
    """
    lines: (speaker, text) pairs, e.g. from a merged transcript.
    Returns (speaker, value, kind, context) rows, one per money amount or
    percentage found, in order of appearance. `context` is the full line
    the value was found in, so the table entry is still meaningful without
    the transcript open next to it.
    """
    rows = []
    for speaker, text in lines:
        matches = [(m.start(), m.group().strip(), "Money") for m in _MONEY_RE.finditer(text)]
        matches += [(m.start(), m.group().strip(), "Percentage") for m in _PERCENT_RE.finditer(text)]
        matches.sort(key=lambda m: m[0])
        rows += [(speaker, value, kind, text.strip()) for _pos, value, kind in matches]
    return rows
