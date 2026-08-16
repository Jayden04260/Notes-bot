"""
redact.py

Best-effort, local, regex-based redaction of numbers that look like credit
card numbers or US Social Security Numbers, so they don't end up sitting in
a plaintext transcript. Not a substitute for not saying sensitive numbers on
a call in the first place - this only catches what's easy to catch.
"""

import re

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# First digit, then 12-18 more (digit, optionally preceded by a separator) -
# always ends on a digit so a trailing space/dash never gets pulled into
# the match.
_CARD_CANDIDATE_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _redact_card(match: re.Match) -> str:
    digits = re.sub(r"[ -]", "", match.group())
    if len(digits) in (13, 14, 15, 16, 17, 18, 19) and _luhn_valid(digits):
        return "[REDACTED-CARD]"
    return match.group()


def redact(text: str) -> str:
    text = _SSN_RE.sub("[REDACTED-SSN]", text)
    text = _CARD_CANDIDATE_RE.sub(_redact_card, text)
    return text
