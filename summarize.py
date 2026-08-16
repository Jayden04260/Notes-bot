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

from sklearn.feature_extraction.text import TfidfVectorizer

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


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
        vectorizer = TfidfVectorizer(stop_words="english")
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
