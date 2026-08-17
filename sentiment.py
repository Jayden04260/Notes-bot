"""
sentiment.py

Lightweight, local tone analysis via VADER (lexicon/rule-based, no model
download, English-tuned). Produces a per-speaker "Tone" summary line and a
"Tense Moments" list of the most negative-scoring lines.

VADER is built for short, informal text (its lexicon comes from social
media), which fits a call transcript reasonably well, but it's still a
rough indicator - sarcasm, filler ("yeah, right..."), and very short lines
can mis-score. Treat this as a pointer to skim, not a verdict.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# VADER's compound score ranges -1 (most negative) to +1 (most positive).
# Its own docs suggest +/-0.05 as the neutral cutoff.
_POSITIVE_THRESHOLD = 0.05
_NEGATIVE_THRESHOLD = -0.05
# Lines scoring at or below this are "tense" - stricter than the plain
# negative cutoff so the section only surfaces real friction, not mild
# grumbling.
_TENSE_THRESHOLD = -0.5
_MAX_TENSE_MOMENTS = 5

_analyzer = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def score_lines(lines: list[tuple[str, str]]) -> list[tuple[str, str, float]]:
    """
    lines: (speaker, text) pairs.
    Returns (speaker, text, compound_score) for each line with non-empty
    text, in the same order.
    """
    analyzer = _get_analyzer()
    scored = []
    for speaker, text in lines:
        if not text.strip():
            continue
        compound = analyzer.polarity_scores(text)["compound"]
        scored.append((speaker, text, compound))
    return scored


def summarize_tone(scored: list[tuple[str, str, float]]) -> dict[str, str]:
    """
    Average each speaker's compound scores into a Positive/Neutral/Negative
    label, in order of first appearance.
    """
    totals: dict[str, list[float]] = {}
    for speaker, _text, compound in scored:
        totals.setdefault(speaker, []).append(compound)

    result = {}
    for speaker, scores in totals.items():
        avg = sum(scores) / len(scores)
        if avg >= _POSITIVE_THRESHOLD:
            label = "Positive"
        elif avg <= _NEGATIVE_THRESHOLD:
            label = "Negative"
        else:
            label = "Neutral"
        result[speaker] = label
    return result


def find_tense_moments(scored: list[tuple[str, str, float]]) -> list[tuple[str, str]]:
    """
    Return the most negative-scoring lines (compound <= _TENSE_THRESHOLD),
    most negative first, capped at _MAX_TENSE_MOMENTS so a rough call
    doesn't turn this into a wall of text.
    """
    tense = [(speaker, text, compound) for speaker, text, compound in scored if compound <= _TENSE_THRESHOLD]
    tense.sort(key=lambda row: row[2])
    return [(speaker, text) for speaker, text, _compound in tense[:_MAX_TENSE_MOMENTS]]
