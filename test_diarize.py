from diarize import apply_diarization, closest_speaker


def test_closest_speaker_picks_greatest_overlap():
    turns = [(0.0, 2.0, "SPEAKER_00"), (2.0, 5.0, "SPEAKER_01")]
    assert closest_speaker(1.5, 3.0, turns) == "SPEAKER_01"


def test_closest_speaker_returns_none_when_no_overlap():
    turns = [(0.0, 2.0, "SPEAKER_00")]
    assert closest_speaker(5.0, 6.0, turns) is None


def test_apply_diarization_relabels_them_rows():
    combined = [
        (0.0, 1.0, "You", "hello", False),
        (1.0, 2.0, "Them", "hi there", False),
        (3.0, 4.0, "Them", "how are you", False),
    ]
    turns = [(1.0, 2.0, "SPEAKER_00"), (3.0, 4.0, "SPEAKER_01")]

    result = apply_diarization(combined, turns)

    assert result[0][2] == "You"
    assert result[1][2] == "Them (SPEAKER_00)"
    assert result[2][2] == "Them (SPEAKER_01)"


def test_apply_diarization_leaves_unmatched_them_rows_unchanged():
    combined = [(10.0, 11.0, "Them", "unmatched", False)]
    turns = [(0.0, 1.0, "SPEAKER_00")]

    result = apply_diarization(combined, turns)

    assert result[0][2] == "Them"
