"""
summarize.py

A small, local, dependency-light extractive summarizer used to generate a
"Key Points" section for the call notes. It's a simplified TextRank:
sentences are embedded with TF-IDF, scored by their total similarity to
every other sentence, and the top-scoring sentences are kept in their
original order. No LLM/API call and no large model download required.
"""

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def summarize(text: str, num_sentences: int = 5) -> list[str]:
    """Return up to `num_sentences` of the most representative sentences from `text`."""
    sentences = split_sentences(text)
    if len(sentences) <= num_sentences:
        return sentences

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform(sentences)
    except ValueError:
        # e.g. every "sentence" was pure stopwords/punctuation
        return sentences[:num_sentences]

    similarity = (tfidf * tfidf.T).toarray()
    scores = similarity.sum(axis=1)

    top_idx = np.argsort(scores)[::-1][:num_sentences]
    top_idx = sorted(top_idx)  # restore original chronological order

    return [sentences[i] for i in top_idx]
