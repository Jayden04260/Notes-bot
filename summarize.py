"""
summarize.py

A small, local, dependency-light extractive summarizer used to generate a
"Key Points" section for the call notes. It's a simplified TextRank:
sentences are embedded with TF-IDF and scored by their average similarity to
every other sentence (a centrality score - how representative a sentence is
of the whole transcript). Sentences are then picked with Maximal Marginal
Relevance (MMR): each pick maximizes its own centrality while being
penalized for overlapping with sentences already chosen, so the summary
covers more distinct ground instead of a handful of near-duplicate lines
that all happened to score well. No LLM/API call and no large model
download required.
"""

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Titles and abbreviations whose full stop doesn't end a sentence. Whisper
# writes "Mr. Quilter", so a plain split-on-full-stop turned every titled
# name into a bogus one-word "sentence" - which then showed up as a Key
# Point bullet reading just "Mr.".
_ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "approx", "no"}

# Honorifics are everywhere in transcripts and say nothing about the topic
# ("mr" was the top Topics term on a test call).
_STOP_WORDS = list(ENGLISH_STOP_WORDS | {"mr", "mrs", "ms", "dr"})


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for piece in _SENTENCE_SPLIT_RE.split(text.strip()):
        piece = piece.strip()
        if not piece:
            continue
        last_word = sentences[-1].rsplit(None, 1)[-1].rstrip(".").lower() if sentences else ""
        if sentences and sentences[-1].endswith(".") and last_word in _ABBREVIATIONS:
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)
    return sentences


def summarize(text: str, num_sentences: int = 5, diversity: float = 0.3) -> list[str]:
    """
    Return up to `num_sentences` of the most representative sentences from
    `text`. `diversity` (0-1) controls how strongly near-duplicate sentences
    are penalized - 0 reduces to plain top-k centrality, higher values favor
    covering more distinct topics.
    """
    sentences = split_sentences(text)
    if len(sentences) <= num_sentences:
        return sentences

    try:
        vectorizer = TfidfVectorizer(stop_words=_STOP_WORDS)
        tfidf = vectorizer.fit_transform(sentences)
    except ValueError:
        # e.g. every "sentence" was pure stopwords/punctuation
        return sentences[:num_sentences]

    similarity = (tfidf * tfidf.T).toarray()
    relevance = similarity.mean(axis=1)

    selected: list[int] = []
    candidates = set(range(len(sentences)))
    for _ in range(num_sentences):
        if not candidates:
            break
        if not selected:
            best = max(candidates, key=lambda i: relevance[i])
        else:
            best = max(
                candidates,
                key=lambda i: (1 - diversity) * relevance[i]
                - diversity * max(similarity[i][j] for j in selected),
            )
        selected.append(best)
        candidates.discard(best)

    selected.sort()  # restore original chronological order
    return [sentences[i] for i in selected]


def extract_keywords(text: str, num_keywords: int = 8) -> list[str]:
    """
    Return up to `num_keywords` terms with the highest aggregate TF-IDF
    weight across the transcript - a cheap "what was this call about" topic
    list, reusing the same vectorizer approach as summarize().
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words=_STOP_WORDS)
        tfidf = vectorizer.fit_transform(sentences)
    except ValueError:
        return []

    scores = tfidf.sum(axis=0).tolist()[0]
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(scores, terms), reverse=True)
    return [term for score, term in ranked[:num_keywords] if score > 0]
