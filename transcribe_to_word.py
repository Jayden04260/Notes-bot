"""
transcribe_to_word.py

Transcribes the mic + speaker recordings with faster-whisper (runs locally,
no audio ever leaves your machine) and writes a timestamped, speaker-labeled
transcript into a .docx file, with an optional auto-generated "Key Points"
summary at the top.
"""

from pathlib import Path

from docx import Document
from faster_whisper import WhisperModel

from summarize import summarize

# Model size options (bigger = more accurate, slower, more memory):
#   tiny, base, small, medium, large-v3
DEFAULT_MODEL_SIZE = "tiny"

Segment = tuple[float, float, str]
LabeledSegment = tuple[float, float, str, str]


def transcribe(file_path: str | Path, model: WhisperModel) -> list[Segment]:
    """Run Whisper on a wav file, return a list of (start, end, text) tuples."""
    segments, _ = model.transcribe(str(file_path), vad_filter=True)
    return [(seg.start, seg.end, seg.text.strip()) for seg in segments]


def merge_segments(mic_segments: list[Segment], speaker_segments: list[Segment]) -> list[LabeledSegment]:
    """
    Combine the two speaker tracks into one chronological list of
    (start, end, speaker_label, text) tuples, dropping empty segments.
    Pure function - no I/O - so it's easy to unit test.
    """
    combined = [(s, e, "You", t) for s, e, t in mic_segments if t.strip()]
    combined += [(s, e, "Them", t) for s, e, t in speaker_segments if t.strip()]
    combined.sort(key=lambda row: row[0])
    return combined


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def build_doc(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    output_path: str | Path,
    title: str = "Call Notes",
    include_summary: bool = True,
) -> None:
    combined = merge_segments(mic_segments, speaker_segments)

    doc = Document()
    doc.add_heading(title, level=1)

    if include_summary and combined:
        full_text = " ".join(text for *_rest, text in combined)
        key_points = summarize(full_text, num_sentences=5)
        if key_points:
            doc.add_heading("Key Points", level=2)
            for point in key_points:
                doc.add_paragraph(point, style="List Bullet")

    doc.add_heading("Transcript", level=2)
    for start, _end, speaker, text in combined:
        p = doc.add_paragraph()
        run = p.add_run(f"[{format_time(start)}] {speaker}: ")
        run.bold = True
        p.add_run(text)

    doc.save(output_path)


def load_model(model_size: str = DEFAULT_MODEL_SIZE, cpu_threads: int = 4) -> WhisperModel:
    print(f"Loading Whisper model '{model_size}' (first run downloads it, then it's cached)...")
    return WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=cpu_threads, num_workers=1)


def transcribe_call(
    mic_file: str | Path,
    speaker_file: str | Path,
    output_file: str | Path,
    model_size: str = DEFAULT_MODEL_SIZE,
    include_summary: bool = True,
) -> None:
    model = load_model(model_size)

    print("Transcribing your audio...")
    mic_segments = transcribe(mic_file, model)
    print("Transcribing the other side...")
    speaker_segments = transcribe(speaker_file, model)

    build_doc(mic_segments, speaker_segments, output_file, include_summary=include_summary)
    print(f"\nDone. Saved to {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe a recorded call into a Word document.")
    parser.add_argument("mic_wav", help="Path to the mic recording (.wav)")
    parser.add_argument("speaker_wav", help="Path to the speaker/loopback recording (.wav)")
    parser.add_argument("-o", "--output", default="call_notes.docx", help="Output .docx path")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE, choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--no-summary", action="store_true", help="Skip the auto-generated Key Points section")
    args = parser.parse_args()

    transcribe_call(
        args.mic_wav,
        args.speaker_wav,
        args.output,
        model_size=args.model,
        include_summary=not args.no_summary,
    )


if __name__ == "__main__":
    main()
