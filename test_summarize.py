from summarize import split_sentences, summarize


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
