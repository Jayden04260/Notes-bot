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
        mention = clean_mention(ent.text, ent.label_)
        if mention is None:
            continue
        category = _LABEL_NAMES[ent.label_]
        bucket = result.setdefault(category, [])
        if mention not in bucket:
            bucket.append(mention)
    return result


def clean_mention(text: str, label: str) -> str | None:
    """Tidy one entity, or None to drop it.

    - Possessives are stripped, so "Leighton's" and "Leighton" dedupe.
    - People/organisations/places written all in lowercase are dropped:
      Whisper capitalises real names, so a lowercase "entity" is the small
      spaCy model mislabelling a common word - e.g. "us" tagged as a place
      (the US) on a test call. Dates are exempt ("next friday" is a real date).
    """
    mention = text.strip()
    for suffix in ("'s", "’s"):
        if mention.endswith(suffix):
            mention = mention[: -len(suffix)]
    if not mention:
        return None
    if label != "DATE" and mention == mention.lower():
        return None
    return mention
