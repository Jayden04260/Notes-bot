"""
transcribe_to_word.py

Transcribes the mic + speaker recordings with faster-whisper (runs locally,
no audio ever leaves your machine) and writes a timestamped, speaker-labeled
transcript into a .docx file, with an optional auto-generated "Key Points"
summary, an "Action Items" section, and redaction of numbers that look like
credit cards/SSNs.
"""

from pathlib import Path

from docx import Document
from faster_whisper import WhisperModel

from action_items import find_action_items
from redact import redact
from summarize import summarize

# Model size options (bigger = more accurate, slower, more memory):
#   tiny, base, small, medium, large-v3
DEFAULT_MODEL_SIZE = "small"

# Used unless the caller passes their own --prompt: nudges Whisper toward
# treating this as clean call audio rather than e.g. music/noise.
DEFAULT_INITIAL_PROMPT = "This is a clear call transcript in English."

# Segments with a high no_speech_prob or a very low avg_logprob are usually
# Whisper hallucinating on silence/noise rather than transcribing real
# speech - drop them. Thresholds are the commonly-used defaults for this
# heuristic, not tuned specifically for this project.
NO_SPEECH_THRESHOLD = 0.6
MIN_AVG_LOGPROB = -1.0

Segment = tuple[float, float, str]
LabeledSegment = tuple[float, float, str, str]


def transcribe(file_path: str | Path, model: WhisperModel, initial_prompt: str | None = None) -> list[Segment]:
    """
    Run Whisper on a wav file, return a list of (start, end, text) tuples.
    `initial_prompt` biases Whisper's vocabulary (e.g. names, jargon that
    tend to come up on your calls) - see faster-whisper's docs.
    """
    segments, _ = model.transcribe(
        str(file_path),
        language="en",
        beam_size=5,
        temperature=0.0,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        initial_prompt=initial_prompt or DEFAULT_INITIAL_PROMPT,
    )
    result = []
    for seg in segments:
        if seg.no_speech_prob > NO_SPEECH_THRESHOLD or seg.avg_logprob < MIN_AVG_LOGPROB:
            continue
        result.append((seg.start, seg.end, seg.text.strip()))
    return result


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


def _prepare_notes(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    include_summary: bool,
    include_action_items: bool,
    redact_text: bool,
) -> tuple[list[LabeledSegment], list[str], list[tuple[str, str]]]:
    combined = merge_segments(mic_segments, speaker_segments)
    if redact_text:
        combined = [(s, e, speaker, redact(text)) for s, e, speaker, text in combined]

    key_points = []
    if include_summary and combined:
        full_text = " ".join(text for *_rest, text in combined)
        key_points = summarize(full_text, num_sentences=5)

    action_items = []
    if include_action_items and combined:
        action_items = find_action_items([(speaker, text) for *_rest, speaker, text in combined])

    return combined, key_points, action_items


def build_doc(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    output_path: str | Path,
    title: str = "Call Notes",
    include_summary: bool = True,
    include_action_items: bool = True,
    redact_text: bool = True,
) -> None:
    combined, key_points, action_items = _prepare_notes(
        mic_segments, speaker_segments, include_summary, include_action_items, redact_text
    )

    doc = Document()
    doc.add_heading(title, level=1)

    if key_points:
        doc.add_heading("Key Points", level=2)
        for point in key_points:
            doc.add_paragraph(point, style="List Bullet")

    if action_items:
        doc.add_heading("Action Items", level=2)
        for speaker, text in action_items:
            doc.add_paragraph(f"{speaker}: {text}", style="List Bullet")

    doc.add_heading("Transcript", level=2)
    for start, _end, speaker, text in combined:
        p = doc.add_paragraph()
        run = p.add_run(f"[{format_time(start)}] {speaker}: ")
        run.bold = True
        p.add_run(text)

    doc.save(output_path)


def build_markdown(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    output_path: str | Path,
    title: str = "Call Notes",
    include_summary: bool = True,
    include_action_items: bool = True,
    redact_text: bool = True,
) -> None:
    combined, key_points, action_items = _prepare_notes(
        mic_segments, speaker_segments, include_summary, include_action_items, redact_text
    )

    lines = [f"# {title}", ""]

    if key_points:
        lines.append("## Key Points")
        lines.append("")
        lines += [f"- {point}" for point in key_points]
        lines.append("")

    if action_items:
        lines.append("## Action Items")
        lines.append("")
        lines += [f"- **{speaker}:** {text}" for speaker, text in action_items]
        lines.append("")

    lines.append("## Transcript")
    lines.append("")
    lines += [f"**[{format_time(start)}] {speaker}:** {text}" for start, _end, speaker, text in combined]

    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_model(model_size: str = DEFAULT_MODEL_SIZE, cpu_threads: int = 4) -> WhisperModel:
    print(f"Loading Whisper model '{model_size}' (first run downloads it, then it's cached)...")
    return WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=cpu_threads, num_workers=1)


def transcribe_call(
    mic_file: str | Path,
    speaker_file: str | Path,
    output_file: str | Path,
    model_size: str = DEFAULT_MODEL_SIZE,
    include_summary: bool = True,
    include_action_items: bool = True,
    redact_text: bool = True,
    initial_prompt: str | None = None,
    markdown: bool = False,
) -> None:
    model = load_model(model_size)

    print("Transcribing your audio...")
    mic_segments = transcribe(mic_file, model, initial_prompt=initial_prompt)
    print("Transcribing the other side...")
    speaker_segments = transcribe(speaker_file, model, initial_prompt=initial_prompt)

    build_doc(
        mic_segments,
        speaker_segments,
        output_file,
        include_summary=include_summary,
        include_action_items=include_action_items,
        redact_text=redact_text,
    )
    print(f"\nDone. Saved to {output_file}")

    if markdown:
        md_path = Path(output_file).with_suffix(".md")
        build_markdown(
            mic_segments,
            speaker_segments,
            md_path,
            include_summary=include_summary,
            include_action_items=include_action_items,
            redact_text=redact_text,
        )
        print(f"Also saved to {md_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe a recorded call into a Word document.")
    parser.add_argument("mic_wav", help="Path to the mic recording (.wav)")
    parser.add_argument("speaker_wav", help="Path to the speaker/loopback recording (.wav)")
    parser.add_argument("-o", "--output", default="call_notes.docx", help="Output .docx path")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE, choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--no-summary", action="store_true", help="Skip the auto-generated Key Points section")
    parser.add_argument("--no-action-items", action="store_true", help="Skip the auto-detected Action Items section")
    parser.add_argument("--no-redact", action="store_true", help="Don't redact numbers that look like cards/SSNs")
    parser.add_argument("--prompt", default=None, help="Initial prompt to bias Whisper's vocabulary (names, jargon)")
    parser.add_argument("--markdown", action="store_true", help="Also write a .md version alongside the .docx")
    args = parser.parse_args()

    transcribe_call(
        args.mic_wav,
        args.speaker_wav,
        args.output,
        model_size=args.model,
        include_summary=not args.no_summary,
        include_action_items=not args.no_action_items,
        redact_text=not args.no_redact,
        initial_prompt=args.prompt,
        markdown=args.markdown,
    )


if __name__ == "__main__":
    main()
