from transcribe_to_word import format_time, merge_segments


def test_format_time_under_a_minute():
    assert format_time(5) == "00:05"


def test_format_time_over_a_minute():
    assert format_time(125) == "02:05"


def test_merge_segments_chronological_order():
    mic = [(2.0, 3.0, "I think so", False), (0.0, 1.0, "Hello", False)]
    speaker = [(1.0, 2.0, "Hi there", False)]

    merged = merge_segments(mic, speaker)

    assert [row[0] for row in merged] == [0.0, 1.0, 2.0]
    assert [row[2] for row in merged] == ["You", "Them", "You"]


def test_merge_segments_drops_empty_text():
    mic = [(0.0, 1.0, "", False), (1.0, 2.0, "Real text", False)]
    speaker = [(0.5, 1.5, "   ", False)]

    merged = merge_segments(mic, speaker)

    assert len(merged) == 1
    assert merged[0][3] == "Real text"


def test_merge_segments_preserves_low_confidence_flag():
    mic = [(0.0, 1.0, "Not sure about this", True)]
    speaker = [(1.0, 2.0, "This one is clear", False)]

    merged = merge_segments(mic, speaker)

    assert merged[0][4] is True
    assert merged[1][4] is False
