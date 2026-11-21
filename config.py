"""
config.py

Shared constants that need to be readable without pulling in faster-whisper/
scikit-learn (those imports take several seconds - see transcribe_to_word.py)
so run.py can build its CLI and start recording immediately.
"""

# Model size options (bigger = more accurate, slower, more memory):
#   tiny, base, small, medium, large-v3, large-v3-turbo
# "auto" (the CLI default) picks GPU_DEFAULT_MODEL_SIZE when an NVIDIA GPU
# is usable and DEFAULT_MODEL_SIZE otherwise - see README "How accurate is it?".
MODEL_CHOICES = ["auto", "tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
DEFAULT_MODEL_SIZE = "small"
GPU_DEFAULT_MODEL_SIZE = "large-v3-turbo"


def add_model_arguments(parser) -> None:
    """--model / --device / --language, shared by run.py and transcribe_to_word.py."""
    parser.add_argument(
        "--model",
        default="auto",
        choices=MODEL_CHOICES,
        help=f"Whisper model size - bigger is more accurate but slower/more memory. 'auto' (default) uses "
        f"{GPU_DEFAULT_MODEL_SIZE} on an NVIDIA GPU, {DEFAULT_MODEL_SIZE} on CPU",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Where to run transcription: 'auto' (default) uses an NVIDIA GPU if one is usable "
        "(see requirements-gpu.txt), else the CPU",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Whisper language code for the call (default: en), or 'auto' to detect it. Key Points, "
        "Action Items etc. are still English-tuned.",
    )
