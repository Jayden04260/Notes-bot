"""
action_items.py

Lightweight, local, rule-based action-item detector: flags transcript lines
that read like a commitment, request, or deadline. No LLM/API call - just
phrase matching, so it's cheap and easy to unit test.

Measured with eval_action_items.py against hand-labelled call lines
(eval/action_items_labeled.json). The original keyword list flagged
anything containing "going to", "can you", "need to"... - so "I'm going to
be honest", "Can you hear me?" and "It's going to rain" all became action
items, and about half of what it flagged wasn't one (precision 0.40-0.54).
The rules below are grouped by what makes something an action item:

- commitments are first-person ("I'll", "we're going to"), not "it's going
  to rain" or "they're going to love it";
- requests are "can/could/would you" + something to do, not the call-
  mechanics questions every call is full of ("can you hear me?");
- conversational set phrases built from the same words ("I'll be honest",
  "let's be real", "I will say") are excluded explicitly;
- polite imperatives ("please send...", "would you mind...", "remind me
  to...") and due dates ("due on the 14th") are caught, which the old list
  missed entirely.
"""

import re

_DAY = (
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|tonight|"
    r"eod|cob|end of (?:the )?(?:day|week|month)|next week|the \d{1,2}(?:st|nd|rd|th)?)"
)

# Set phrases built from action-ish words that aren't actions: "I'll be
# honest", "let's be real", "I will say...", "we'll see".
_FILLER = r"(?:be honest|be real|be frank|say\b|see\b)"

# Call-mechanics questions: "can you hear me", "could you repeat that".
_CALL_MECHANICS = r"(?:hear|see|repeat|believe)\b"

_ACTION_PATTERNS = [
    # First-person commitments
    rf"\b(?:i|we)(?:'ll| will| shall)\b(?!\s+{_FILLER})",
    rf"\b(?:i'm|i am|we're|we are) going to\b(?!\s+{_FILLER})",
    r"\b(?:i|we) can (?:take care of|handle|send|do|sort|look into)\b",
    # Requests
    rf"\b(?:can|could|would) you\b(?!\s+(?:please\s+)?{_CALL_MECHANICS})",
    r"\bwould you mind\b",
    r"(?:^|[.!?,]\s*)please\s+\w+",
    r"\bremind me to\b",
    r"\bdon'?t forget\b",
    r"\bmake sure\b",
    # Obligations
    rf"\b(?:i|we|you|they|he|she) (?:need|needs|have|has) to\b(?!\s+{_FILLER})",
    r"\b(?:we|you) should\b(?!\s+see\b)",
    rf"\blet'?s\b(?!\s+{_FILLER})",
    r"\blet me (?:check|confirm|look into|find out|follow up|get back|send|ask|chase)\b",
    # Follow-ups and explicit markers
    r"\bfollow(?:ing)? up\b",
    r"\bget back to you\b",
    r"\baction item\b",
    # Deadlines
    rf"\bby {_DAY}\b",
    r"\bdue (?:on|by)\b",
]

_ACTION_RE = re.compile("|".join(_ACTION_PATTERNS), re.IGNORECASE)


def find_action_items(lines: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    lines: (speaker, text) pairs, e.g. from a merged transcript.
    Returns the subset that look like action items, in the same order.
    """
    return [(speaker, text) for speaker, text in lines if _ACTION_RE.search(text)]
