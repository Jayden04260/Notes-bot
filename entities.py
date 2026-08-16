"""
entities.py

Named-entity extraction (people, organizations, dates, places) via spaCy's
small English pipeline, used to build a "Mentioned" section separate from
the rule-based Action Items list. Runs locally - no API call - but does
pull in spaCy and a ~13MB model download on first use
(`python -m spacy download en_core_web_sm`).
"""

_KEEP_LABELS = {"PERSON", "ORG", "DATE", "GPE"}
_LABEL_NAMES = {"PERSON": "People", "ORG": "Organizations", "DATE": "Dates", "GPE": "Places"}

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy

        try:
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
        except OSError as exc:
            raise RuntimeError(
                "spaCy's English model isn't installed. Run: python -m spacy download en_core_web_sm"
            ) from exc
    return _nlp


def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Return {category_name: [unique mentions in order of first appearance]}
    for people, organizations, dates, and places found in `text`. Raises
    RuntimeError (via _get_nlp) if spaCy/the model aren't installed - callers
    should catch that and skip the section rather than fail the whole run.
    """
    if not text.strip():
        return {}

    doc = _get_nlp()(text)
    result: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ not in _KEEP_LABELS:
            continue
        category = _LABEL_NAMES[ent.label_]
        bucket = result.setdefault(category, [])
        if ent.text not in bucket:
            bucket.append(ent.text)
    return result
