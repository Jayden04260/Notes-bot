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
    parser.add_argument("--no-redact", action="store_true", help="Don't redact numbers that look like cards/SSNs")
    parser.add_argument("--prompt", default=None, help="Initial prompt to bias Whisper's vocabulary (names, jargon)")
    parser.add_argument("--markdown", action="store_true", help="Also write a .md version alongside the .docx")
    args = parser.parse_args()

    mic_file, speaker_file = record_call()

    # Deferred: faster-whisper/scikit-learn take several seconds to import,
    # which would otherwise delay the "press Enter to record" prompt above.
    from transcribe_to_word import transcribe_call

    output_file = Path("recordings") / f"call_notes_{time.strftime('%Y%m%d_%H%M%S')}.docx"
    transcribe_call(
        mic_file,
        speaker_file,
        str(output_file),
        model_size=args.model,
        include_summary=not args.no_summary,
        include_action_items=not args.no_action_items,
        redact_text=not args.no_redact,
        initial_prompt=args.prompt,
        markdown=args.markdown,
    )


if __name__ == "__main__":
    main()
