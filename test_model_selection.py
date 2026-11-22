from config import DEFAULT_MODEL_SIZE, GPU_DEFAULT_MODEL_SIZE
from transcribe_to_word import resolve_model_size


def test_auto_picks_the_bigger_model_only_on_gpu():
    assert resolve_model_size("auto", "cuda") == GPU_DEFAULT_MODEL_SIZE
    assert resolve_model_size("auto", "cpu") == DEFAULT_MODEL_SIZE


def test_an_explicit_model_choice_is_always_kept():
    assert resolve_model_size("medium", "cuda") == "medium"
    assert resolve_model_size("large-v3-turbo", "cpu") == "large-v3-turbo"
