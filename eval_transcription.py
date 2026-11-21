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

WER here is the standard word-level edit distance (substitutions +
deletions + insertions) over the number of reference words, after
lowercasing and stripping punctuation from both sides - implemented
directly (wer() below) rather than adding a dependency for 20 lines.
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
    """Levenshtein distance between two word sequences."""
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


def wer(references: list[str], hypotheses: list[str]) -> float:
    errors = total = 0
    for ref, hyp in zip(references, hypotheses):
        ref_words = normalize(ref)
        errors += word_errors(ref_words, normalize(hyp))
        total += len(ref_words)
    return errors / max(total, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Word error rate + speed of the transcription step.")
    parser.add_argument("clips_dir", help="Folder of .wav files with a references.json")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
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

    score = wer([references[n] for n in names], hypotheses)
    print(
        f"model={args.model} device={model.notes_bot_device} clips={len(names)} "
        f"audio={audio_seconds / 60:.1f}min  WER={score:.2%}  "
        f"time={elapsed:.1f}s  speed={audio_seconds / elapsed:.1f}x real-time"
    )


if __name__ == "__main__":
    main()
