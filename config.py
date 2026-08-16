"""
config.py

Shared constants that need to be readable without pulling in faster-whisper/
scikit-learn (those imports take several seconds - see transcribe_to_word.py)
so run.py can build its CLI and start recording immediately.
"""

# Model size options (bigger = more accurate, slower, more memory):
#   tiny, base, small, medium, large-v3
DEFAULT_MODEL_SIZE = "small"
