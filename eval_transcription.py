"""
eval_transcription.py

Measures transcription accuracy (word error rate) and speed for a given
Whisper model size / device, against a folder of reference clips - the
number this project never had before: "how accurate is the transcript?"
was previously unmeasured.

The folder needs .wav files plus a references.json mapping each file name
to its correct transcript, e.g. {"clip1.wav": "HELLO THERE", ...}. Any
public read-speech set works; the README's numbers use the 73-clip
LibriSpeech sample at hf-internal-testing/librispeech_asr_dummy (8 minutes
of clean read speech - see README "How accurate is it?" for how to fetch it).

Usage:
    python eval_transcription.py <clips_dir> [--model small] [--device auto|cpu|cuda]

WER is the standard word-level edit distance (substitutions + deletions +
insertions) over the number of reference words. Two versions are reported:

- basic: lowercase, punctuation stripped. Counts formatting differences as
  errors ("Mr." vs "mister", "1990" vs "nineteen ninety", "colour" vs
  "color", fillers like "um") - pessimistic.
- whisper-normalised: OpenAI's Whisper EnglishTextNormalizer (the
  `whisper-normalizer` package, in requirements-dev.txt) applied to both
  sides first - the standard way Whisper WERs are reported, so it's the one
  to compare with published numbers.

--save writes every clip's reference/hypothesis pair to a JSON file, for
looking at what kind of errors remain.
"""

import argparse
import json
import re
import time
from pathlib import Path

from config import DEFAULT_MODEL_SIZE

_NON_WORD_RE = re.compile(r"[^a-z0-9' ]+")


def normalize(text: str) -> list[str]:
    text = _NON_WORD_RE.sub(" ", text.lower().replace("-", " "))
    return text.split()


def word_errors(reference: list[str], hypothesis: list[str]) -> int:
    """Levenshtein distance between two word sequences. Uses rapidfuzz (C) if
    installed - whole-call transcripts are thousands of words, where the pure-
    Python version below takes about a minute per call."""
    try:
        from rapidfuzz.distance import Levenshtein

        return Levenshtein.distance(reference, hypothesis)
    except ImportError:
        pass
    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, 1):
        current = [i] + [0] * len(hypothesis)
        for j, hyp_word in enumerate(hypothesis, 1):
            current[j] = min(
                previous[j] + 1,  # deletion
                current[j - 1] + 1,  # insertion
                previous[j - 1] + (ref_word != hyp_word),  # substitution / match
            )
        previous = current
    return previous[-1]


def wer(references: list[str], hypotheses: list[str], normalizer=normalize) -> float:
    errors = total = 0
    for ref, hyp in zip(references, hypotheses):
        ref_words = normalizer(ref)
        errors += word_errors(ref_words, normalizer(hyp))
        total += len(ref_words)
    return errors / max(total, 1)


def whisper_normalizer():
    """Word-list normaliser using Whisper's EnglishTextNormalizer, or None if
    the optional whisper-normalizer package isn't installed."""
    try:
        from whisper_normalizer.english import EnglishTextNormalizer
    except ImportError:
        return None
    english = EnglishTextNormalizer()
    return lambda text: english(text).split()


def main() -> None:
    parser = argparse.ArgumentParser(description="Word error rate + speed of the transcription step.")
    parser.add_argument("clips_dir", help="Folder of .wav files with a references.json")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--save", default=None, help="Write per-clip reference/hypothesis pairs to this JSON file")
    args = parser.parse_args()

    import wave

    from transcribe_to_word import load_model, transcribe

    def duration(path: Path) -> float:
        with wave.open(str(path)) as wf:
            return wf.getnframes() / wf.getframerate()

    clips_dir = Path(args.clips_dir)
    references = json.loads((clips_dir / "references.json").read_text(encoding="utf-8"))
    names = sorted(references)
    audio_seconds = sum(duration(clips_dir / name) for name in names)

    model = load_model(args.model, device=args.device)
    # Warm-up on one clip: the first call pays one-off costs (on a GPU newer
    # than the CTranslate2 build, compiling kernels can take ~30s) that a
    # real call's transcription would only pay once per run, not per clip.
    transcribe(clips_dir / names[0], model)

    start = time.perf_counter()
    hypotheses = [" ".join(seg[2] for seg in transcribe(clips_dir / name, model)) for name in names]
    elapsed = time.perf_counter() - start

    refs = [references[n] for n in names]
    basic = wer(refs, hypotheses)
    normalizer = whisper_normalizer()
    normalized = f"{wer(refs, hypotheses, normalizer):.2%}" if normalizer else "n/a (pip install whisper-normalizer)"
    print(
        f"model={args.model} device={model.notes_bot_device} clips={len(names)} "
        f"audio={audio_seconds / 60:.1f}min  WER basic={basic:.2%} whisper-normalised={normalized}  "
        f"time={elapsed:.1f}s  speed={audio_seconds / elapsed:.1f}x real-time"
    )
    if args.save:
        rows = [{"clip": n, "reference": r, "hypothesis": h} for n, r, h in zip(names, refs, hypotheses)]
        Path(args.save).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
