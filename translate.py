"""
translate.py

Optional translation of the call transcript (English <-> Spanish, or any
other language pair Google Translate supports).

This uses deep-translator's free Google Translate backend, which needs
internet access at translate time but has a tiny install footprint (just
`requests` + `beautifulsoup4`, no ML runtime).

Why not a fully offline translator? Local neural MT libraries (e.g. Argos
Translate) pull in PyTorch for their sentence-splitting stage - a large
(~700MB+) install that risks the same out-of-memory problems this project
already hit with Whisper. If you're on a machine with more headroom, it's a
reasonable drop-in swap: replace `translate_text` below with a call into
your local MT engine of choice and everything else (transcript building,
tests) keeps working unchanged.
"""

import time

from deep_translator import GoogleTranslator
from deep_translator.exceptions import RequestError, TranslationNotFound


def translate_text(text, target_lang, source_lang="auto", retries=2, delay=1.0):
    """Translate a single string. Falls back to the original text on repeated failure."""
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    for attempt in range(retries + 1):
        try:
            return translator.translate(text)
        except (RequestError, TranslationNotFound) as exc:
            if attempt == retries:
                print(f"Warning: translation failed for a line ({exc}); keeping original text.")
                return text
            time.sleep(delay)


def translate_segments(segments, target_lang, source_lang="auto", translate_fn=translate_text):
    """
    segments: list of (start, end, speaker, text) tuples, e.g. from merge_segments().
    Returns a new list of the same shape with `text` translated.

    translate_fn is injectable so this can be unit tested without a network call.
    """
    return [
        (start, end, speaker, translate_fn(text, target_lang, source_lang))
        for start, end, speaker, text in segments
    ]
