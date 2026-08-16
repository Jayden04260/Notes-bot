from summarize import extract_keywords, split_sentences, summarize


def test_split_sentences_basic():
    text = "Hello there. How are you? I am fine!"
    assert split_sentences(text) == ["Hello there.", "How are you?", "I am fine!"]


def test_summarize_returns_all_when_short():
    text = "One sentence. Two sentence."
    result = summarize(text, num_sentences=5)
    assert len(result) == 2


def test_summarize_respects_sentence_limit():
    text = " ".join(f"This is sentence number {i} about the project timeline." for i in range(10))
    result = summarize(text, num_sentences=3)
    assert len(result) == 3


def test_summarize_avoids_near_duplicate_sentences():
    sentences = [
        "The budget for next quarter was approved by finance.",
        "Finance approved the budget for next quarter.",
        "The launch timeline was pushed back two weeks.",
        "Someone mentioned lunch plans for tomorrow.",
    ]
    text = " ".join(sentences)
    result = summarize(text, num_sentences=2, diversity=0.5)

    # the two near-duplicate budget sentences shouldn't both be picked
    assert not (sentences[0] in result and sentences[1] in result)


def test_extract_keywords_finds_repeated_topic_terms():
    text = (
        "The budget for next quarter needs sign-off. "
        "Finance is reviewing the budget this week. "
        "Someone mentioned lunch plans for tomorrow. "
        "The final budget number should be ready soon."
    )
    keywords = extract_keywords(text, num_keywords=3)
    assert "budget" in keywords


def test_extract_keywords_respects_limit():
    text = " ".join(f"This is sentence number {i} about the quarterly roadmap." for i in range(10))
    keywords = extract_keywords(text, num_keywords=3)
    assert len(keywords) <= 3


def test_extract_keywords_empty_text():
    assert extract_keywords("") == []


def test_summarize_preserves_original_order():
    sentences = [
        "The budget was approved for next quarter.",
        "We discussed the weather briefly.",
        "The timeline was pushed back two weeks due to budget constraints.",
        "Someone mentioned lunch plans.",
        "The final budget number was confirmed by finance.",
    ]
    text = " ".join(sentences)
    result = summarize(text, num_sentences=2)

    # results should appear in the same relative order as the source text
    indices = [sentences.index(s) for s in result]
    assert indices == sorted(indices)
