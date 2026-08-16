"""
action_items.py

Lightweight, local, rule-based action-item detector: flags transcript lines
that read like a commitment, request, or deadline. No LLM/API call - just
keyword/phrase matching, so it's cheap and easy to unit test.
"""

import re

_ACTION_PHRASES = [
    r"\bi'll\b",
    r"\bi will\b",
    r"\bwe'll\b",
    r"\bwe will\b",
    r"\blet's\b",
    r"\bcan you\b",
    r"\bcould you\b",
    r"\bneed(?:s)? to\b",
    r"\bgoing to\b",
    r"\bmake sure\b",
    r"\bfollow up\b",
    r"\baction item\b",
    r"\bby (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|end of day|eod|next week)\b",
]

_ACTION_RE = re.compile("|".join(_ACTION_PHRASES), re.IGNORECASE)


def find_action_items(lines: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    lines: (speaker, text) pairs, e.g. from a merged transcript.
    Returns the subset that look like action items, in the same order.
    """
    return [(speaker, text) for speaker, text in lines if _ACTION_RE.search(text)]
