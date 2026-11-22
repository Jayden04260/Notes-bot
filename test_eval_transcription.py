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


def test_whisper_normalised_wer_ignores_formatting_differences():
    from eval_transcription import whisper_normalizer

    normalizer = whisper_normalizer()
    if normalizer is None:  # optional dev dependency
        import pytest

        pytest.skip("whisper-normalizer not installed")
    refs, hyps = ["MISTER QUILTER IS THE APOSTLE"], ["Mr. Quilter is the apostle."]
    assert wer(refs, hyps) > 0  # basic normalisation counts "mr" vs "mister"
    assert wer(refs, hyps, normalizer) == 0
