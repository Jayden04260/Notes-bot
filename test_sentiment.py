from sentiment import find_tense_moments, score_lines, summarize_tone

POSITIVE_LINE = "This is amazing, great work on the launch!"
NEGATIVE_LINE = "This is a complete disaster and I am furious about it."
NEUTRAL_LINE = "We need to review the timeline before Friday."


def test_score_lines_returns_compound_per_line():
    lines = [("You", POSITIVE_LINE), ("Them", NEGATIVE_LINE)]
    scored = score_lines(lines)
    assert len(scored) == 2
    assert scored[0][0] == "You" and scored[0][1] == POSITIVE_LINE and scored[0][2] > 0.5
    assert scored[1][0] == "Them" and scored[1][1] == NEGATIVE_LINE and scored[1][2] < -0.5


def test_score_lines_skips_empty_text():
    lines = [("You", ""), ("Them", "   "), ("You", NEUTRAL_LINE)]
    scored = score_lines(lines)
    assert len(scored) == 1
    assert scored[0][1] == NEUTRAL_LINE


def test_summarize_tone_labels_per_speaker():
    lines = [
        ("You", POSITIVE_LINE),
        ("You", POSITIVE_LINE),
        ("Them", NEGATIVE_LINE),
        ("Them", NEGATIVE_LINE),
    ]
    tone = summarize_tone(score_lines(lines))
    assert tone == {"You": "Positive", "Them": "Negative"}


def test_summarize_tone_labels_neutral():
    lines = [("You", NEUTRAL_LINE)]
    tone = summarize_tone(score_lines(lines))
    assert tone == {"You": "Neutral"}


def test_find_tense_moments_only_strongly_negative():
    lines = [
        ("You", NEUTRAL_LINE),
        ("Them", "Not great, but we can work with it."),
        ("Them", NEGATIVE_LINE),
    ]
    tense = find_tense_moments(score_lines(lines))
    assert tense == [("Them", NEGATIVE_LINE)]


def test_find_tense_moments_orders_most_negative_first():
    less_negative = "That is absolutely unacceptable and frankly infuriating."
    lines = [("Them", less_negative), ("You", NEGATIVE_LINE)]
    tense = find_tense_moments(score_lines(lines))
    assert tense == [("You", NEGATIVE_LINE), ("Them", less_negative)]


def test_find_tense_moments_caps_at_five():
    lines = [("Them", NEGATIVE_LINE)] * 8
    tense = find_tense_moments(score_lines(lines))
    assert len(tense) == 5


def test_find_tense_moments_empty_when_nothing_negative_enough():
    lines = [("You", POSITIVE_LINE), ("Them", NEUTRAL_LINE)]
    assert find_tense_moments(score_lines(lines)) == []
