"""
run.py

One-command call notes: records your call, then automatically transcribes
it into a Word document with an optional Key Points summary.

Usage:
    python run.py
    python run.py --model base
    python run.py --no-summary
"""

import argparse
import os
import sys
import time
from pathlib import Path

from config import DEFAULT_MODEL_SIZE
from record_call import record_call


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a call and generate Word notes for it.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_SIZE,
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size - bigger is more accurate but slower/more memory (default: %(default)s)",
    )
    parser.add_argument("--no-summary", action="store_true", help="Skip the auto-generated Key Points section")
    parser.add_argument("--no-action-items", action="store_true", help="Skip the auto-detected Action Items section")
    parser.add_argument("--no-topics", action="store_true", help="Skip the auto-extracted Topics line")
    parser.add_argument("--no-mentions", action="store_true", help="Skip the auto-detected Mentioned section")
    parser.add_argument(
        "--no-numbers", action="store_true", help="Skip the auto-detected Numbers Mentioned table"
    )
    parser.add_argument(
        "--no-sentiment", action="store_true", help="Skip the Tone summary and Tense Moments section"
    )
    parser.add_argument("--no-redact", action="store_true", help="Don't redact numbers that look like cards/SSNs")
    parser.add_argument("--prompt", default=None, help="Initial prompt to bias Whisper's vocabulary (names, jargon)")
    parser.add_argument("--markdown", action="store_true", help="Also write a .md version alongside the .docx")
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Split 'Them' into distinct speakers for group calls (needs "
        "requirements-diarize.txt and --hf-token)",
    )
    parser.add_argument(
        "--hf-token", default=os.environ.get("HF_TOKEN"), help="Hugging Face token for --diarize (or set HF_TOKEN)"
    )
    parser.add_argument(
        "--translate",
        default=None,
        metavar="LANG",
        help="Translate the transcript to this language code (e.g. 'es'). Needs "
        "requirements-translate.txt and internet access at translate time. "
        "Skips the interactive translate prompt if set.",
    )
    parser.add_argument(
        "--translate-from",
        default="auto",
        metavar="LANG",
        help="Source language code for --translate (default: auto-detect)",
    )
    args = parser.parse_args()

    print(
        "\nReminder: recording a call may require the other party's consent "
        "under wiretapping/recording laws in your state or country. It's "
        "your responsibility to check the rules that apply to you and get "
        "consent before you record.\n"
    )
    consent = input("Continue? [y/N]: ").strip().lower()
    if consent not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    translate_to = args.translate
    if translate_to is None:
        choice = input(
            "Translate the transcript once it's recorded? Enter a language code "
            "(e.g. 'es', 'fr'), or press Enter to skip: "
        ).strip()
        translate_to = choice or None

    mic_file, speaker_file = record_call()

    # Deferred: faster-whisper/scikit-learn take several seconds to import,
    # which would otherwise delay the "press Enter to record" prompt above.
    from transcribe_to_word import transcribe_call

    output_file = Path("recordings") / f"call_notes_{time.strftime('%Y%m%d_%H%M%S')}.docx"
    try:
        transcribe_call(
            mic_file,
            speaker_file,
            str(output_file),
            model_size=args.model,
            include_summary=not args.no_summary,
            include_action_items=not args.no_action_items,
            include_topics=not args.no_topics,
            include_mentions=not args.no_mentions,
            include_numbers=not args.no_numbers,
            include_sentiment=not args.no_sentiment,
            redact_text=not args.no_redact,
            initial_prompt=args.prompt,
            markdown=args.markdown,
            diarize_speakers=args.diarize,
            hf_token=args.hf_token,
            translate_to=translate_to,
            translate_from=args.translate_from,
        )
    except Exception as exc:
        # This is the top-level safety net: _prepare_notes already isolates
        # each enrichment step, but load_model()/transcribe()/doc.save()
        # itself can still fail (e.g. disk full, output file open in Word,
        # a bad first-run model download). Recording already succeeded by
        # this point, so the one thing that must never happen is losing
        # those files silently along with the transcription error.
        print(
            f"\nTranscription failed: {exc}\n"
            "Your recording is safe though - nothing was lost:\n"
            f"  {mic_file}\n"
            f"  {speaker_file}\n"
            "Retry transcription later without re-recording:\n"
            f'  python transcribe_to_word.py "{mic_file}" "{speaker_file}" -o "{output_file}"'
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
