from eval_transcription import normalize, wer, word_errors


def test_normalize_ignores_case_and_punctuation():
    assert normalize("Mr. Quilter, the APOSTLE!") == ["mr", "quilter", "the", "apostle"]


def test_word_errors_counts_substitutions_insertions_and_deletions():
    ref = ["the", "cat", "sat"]
    assert word_errors(ref, ["the", "cat", "sat"]) == 0
    assert word_errors(ref, ["the", "dog", "sat"]) == 1  # substitution
    assert word_errors(ref, ["the", "cat"]) == 1  # deletion
    assert word_errors(ref, ["the", "big", "cat", "sat"]) == 1  # insertion


def test_wer_is_errors_over_reference_words_across_clips():
    assert wer(["the cat sat", "on the mat"], ["the cat sat", "on a mat"]) == 1 / 6
