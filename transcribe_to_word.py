"""
transcribe_to_word.py

Transcribes the mic + speaker recordings with faster-whisper (runs locally,
no audio ever leaves your machine) and writes a timestamped, speaker-labeled
transcript into a .docx file, with an optional auto-generated "Key Points"
summary, "Topics", "Mentioned" (people/orgs/dates), "Numbers Mentioned"
(money/percentages), "Tone" summary + "Tense Moments", and "Action Items"
sections, and redaction of numbers that look like credit cards/SSNs.
"""

from pathlib import Path

from docx import Document
from faster_whisper import WhisperModel

from action_items import find_action_items
from config import DEFAULT_MODEL_SIZE
from diarize import Turn, apply_diarization
from entities import extract_entities
from numeric_mentions import find_numbers
from redact import redact
from sentiment import find_tense_moments, score_lines, summarize_tone
from summarize import extract_keywords, summarize

# Used unless the caller passes their own --prompt: nudges Whisper toward
# treating this as clean call audio rather than e.g. music/noise.
DEFAULT_INITIAL_PROMPT = "This is a clear call transcript in English."

# no_speech_prob above HARD_NO_SPEECH_THRESHOLD is almost certainly Whisper
# hallucinating on silence/noise - those segments are dropped entirely.
# Segments that are merely below the softer thresholds are kept (they're
# probably real speech) but flagged as low-confidence so you know to
# double-check that line instead of silently losing it.
HARD_NO_SPEECH_THRESHOLD = 0.9
NO_SPEECH_THRESHOLD = 0.6
MIN_AVG_LOGPROB = -1.0

Segment = tuple[float, float, str, bool]
LabeledSegment = tuple[float, float, str, str, bool]


def transcribe(file_path: str | Path, model: WhisperModel, initial_prompt: str | None = None) -> list[Segment]:
    """
    Run Whisper on a wav file, return a list of (start, end, text,
    low_confidence) tuples. `initial_prompt` biases Whisper's vocabulary
    (e.g. names, jargon that tend to come up on your calls) - see
    faster-whisper's docs.
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
        if seg.no_speech_prob > HARD_NO_SPEECH_THRESHOLD:
            continue
        low_confidence = seg.no_speech_prob > NO_SPEECH_THRESHOLD or seg.avg_logprob < MIN_AVG_LOGPROB
        result.append((seg.start, seg.end, seg.text.strip(), low_confidence))
    return result


def merge_segments(mic_segments: list[Segment], speaker_segments: list[Segment]) -> list[LabeledSegment]:
    """
    Combine the two speaker tracks into one chronological list of
    (start, end, speaker_label, text, low_confidence) tuples, dropping
    empty segments. Pure function - no I/O - so it's easy to unit test.
    """
    combined = [(s, e, "You", t, lc) for s, e, t, lc in mic_segments if t.strip()]
    combined += [(s, e, "Them", t, lc) for s, e, t, lc in speaker_segments if t.strip()]
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
    include_topics: bool,
    include_mentions: bool,
    include_numbers: bool,
    include_sentiment: bool,
    redact_text: bool,
    diarization_turns: list[Turn] | None = None,
    translate_to: str | None = None,
    translate_from: str = "auto",
) -> tuple[
    list[LabeledSegment],
    list[str],
    list[str],
    dict[str, list[str]],
    list[tuple[str, str]],
    list[tuple[str, str, str, str]],
    dict[str, str],
    list[tuple[str, str]],
]:
    # Every enrichment step below is independently guarded: a bug or a
    # transient failure (network hiccup, a bad edge case in one analyzer)
    # in any single one of these should cost that one section, not the
    # whole transcript - this is exactly what let a translate/sentiment/etc.
    # crash silently discard an entire successfully-transcribed call before
    # (nothing had been saved to disk yet at that point in the old code).
    combined = merge_segments(mic_segments, speaker_segments)

    if diarization_turns:
        try:
            combined = apply_diarization(combined, diarization_turns)
        except Exception as exc:
            print(f"Skipping diarization labels: {exc}")

    if redact_text:
        try:
            combined = [(s, e, speaker, redact(text), lc) for s, e, speaker, text, lc in combined]
        except Exception as exc:
            print(f"Skipping redaction (numbers won't be masked): {exc}")

    full_text = " ".join(row[3] for row in combined)

    key_points = []
    if include_summary and combined:
        try:
            key_points = summarize(full_text, num_sentences=5)
        except Exception as exc:
            print(f"Skipping Key Points section: {exc}")

    keywords = []
    if include_topics and combined:
        try:
            keywords = extract_keywords(full_text)
        except Exception as exc:
            print(f"Skipping Topics line: {exc}")

    mentions: dict[str, list[str]] = {}
    if include_mentions and combined:
        try:
            mentions = extract_entities(full_text)
        except Exception as exc:
            print(f"Skipping Mentioned section: {exc}")

    action_items = []
    if include_action_items and combined:
        try:
            action_items = find_action_items([(row[2], row[3]) for row in combined])
        except Exception as exc:
            print(f"Skipping Action Items section: {exc}")

    number_mentions: list[tuple[str, str, str, str]] = []
    if include_numbers and combined:
        try:
            number_mentions = find_numbers([(row[2], row[3]) for row in combined])
        except Exception as exc:
            print(f"Skipping Numbers Mentioned section: {exc}")

    tone: dict[str, str] = {}
    tense_moments: list[tuple[str, str]] = []
    if include_sentiment and combined:
        try:
            scored = score_lines([(row[2], row[3]) for row in combined])
            tone = summarize_tone(scored)
            tense_moments = find_tense_moments(scored)
        except Exception as exc:
            print(f"Skipping Tone/Tense Moments sections: {exc}")

    # Translation is applied last, to the displayed transcript only - Key
    # Points/Topics/Mentioned/Numbers Mentioned/Tone/Tense Moments/Action
    # Items above are computed from the original-language text since
    # summarize.py/entities.py/numeric_mentions.py/sentiment.py/
    # action_items.py are English-tuned.
    if translate_to and combined:
        try:
            from translate import translate_text

            print(f"Translating transcript to '{translate_to}'...")
            combined = [
                (s, e, speaker, translate_text(text, translate_to, translate_from), lc)
                for s, e, speaker, text, lc in combined
            ]
        except Exception as exc:
            print(f"Skipping translation, keeping original language: {exc}")

    return combined, key_points, keywords, mentions, action_items, number_mentions, tone, tense_moments


def build_doc(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    output_path: str | Path,
    title: str = "Call Notes",
    include_summary: bool = True,
    include_action_items: bool = True,
    include_topics: bool = True,
    include_mentions: bool = True,
    include_numbers: bool = True,
    include_sentiment: bool = True,
    redact_text: bool = True,
    diarization_turns: list[Turn] | None = None,
    translate_to: str | None = None,
    translate_from: str = "auto",
) -> None:
    combined, key_points, keywords, mentions, action_items, number_mentions, tone, tense_moments = _prepare_notes(
        mic_segments,
        speaker_segments,
        include_summary,
        include_action_items,
        include_topics,
        include_mentions,
        include_numbers,
        include_sentiment,
        redact_text,
        diarization_turns,
        translate_to,
        translate_from,
    )

    doc = Document()
    doc.add_heading(title, level=1)

    if keywords:
        doc.add_paragraph("Topics: " + ", ".join(keywords))

    if tone:
        doc.add_paragraph("Tone: " + ", ".join(f"{speaker} — {label}" for speaker, label in tone.items()))

    if key_points:
        doc.add_heading("Key Points", level=2)
        for point in key_points:
            doc.add_paragraph(point, style="List Bullet")

    if mentions:
        doc.add_heading("Mentioned", level=2)
        for category, names in mentions.items():
            doc.add_paragraph(f"{category}: {', '.join(names)}", style="List Bullet")

    if number_mentions:
        doc.add_heading("Numbers Mentioned", level=2)
        table = doc.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        header = table.rows[0].cells
        header[0].text, header[1].text, header[2].text, header[3].text = "Value", "Type", "Speaker", "Context"
        for speaker, value, kind, context in number_mentions:
            cells = table.add_row().cells
            cells[0].text, cells[1].text, cells[2].text, cells[3].text = value, kind, speaker, context

    if tense_moments:
        doc.add_heading("Tense Moments", level=2)
        for speaker, text in tense_moments:
            doc.add_paragraph(f"{speaker}: {text}", style="List Bullet")

    if action_items:
        doc.add_heading("Action Items", level=2)
        for speaker, text in action_items:
            doc.add_paragraph(f"{speaker}: {text}", style="List Bullet")

    doc.add_heading("Transcript", level=2)
    for start, _end, speaker, text, low_confidence in combined:
        p = doc.add_paragraph()
        run = p.add_run(f"[{format_time(start)}] {speaker}: ")
        run.bold = True
        text_run = p.add_run(f"[uncertain] {text}" if low_confidence else text)
        text_run.italic = low_confidence

    doc.save(output_path)


def build_markdown(
    mic_segments: list[Segment],
    speaker_segments: list[Segment],
    output_path: str | Path,
    title: str = "Call Notes",
    include_summary: bool = True,
    include_action_items: bool = True,
    include_topics: bool = True,
    include_mentions: bool = True,
    include_numbers: bool = True,
    include_sentiment: bool = True,
    redact_text: bool = True,
    diarization_turns: list[Turn] | None = None,
    translate_to: str | None = None,
    translate_from: str = "auto",
) -> None:
    combined, key_points, keywords, mentions, action_items, number_mentions, tone, tense_moments = _prepare_notes(
        mic_segments,
        speaker_segments,
        include_summary,
        include_action_items,
        include_topics,
        include_mentions,
        include_numbers,
        include_sentiment,
        redact_text,
        diarization_turns,
        translate_to,
        translate_from,
    )

    lines = [f"# {title}", ""]

    if keywords:
        lines.append(f"*Topics: {', '.join(keywords)}*")
        lines.append("")

    if tone:
        lines.append("*Tone: " + ", ".join(f"{speaker} — {label}" for speaker, label in tone.items()) + "*")
        lines.append("")

    if key_points:
        lines.append("## Key Points")
        lines.append("")
        lines += [f"- {point}" for point in key_points]
        lines.append("")

    if mentions:
        lines.append("## Mentioned")
        lines.append("")
        lines += [f"- **{category}:** {', '.join(names)}" for category, names in mentions.items()]
        lines.append("")

    if number_mentions:
        lines.append("## Numbers Mentioned")
        lines.append("")
        lines.append("| Value | Type | Speaker | Context |")
        lines.append("| --- | --- | --- | --- |")
        for speaker, value, kind, context in number_mentions:
            escaped_context = context.replace("|", "\\|")
            lines.append(f"| {value} | {kind} | {speaker} | {escaped_context} |")
        lines.append("")

    if tense_moments:
        lines.append("## Tense Moments")
        lines.append("")
        lines += [f"- **{speaker}:** {text}" for speaker, text in tense_moments]
        lines.append("")

    if action_items:
        lines.append("## Action Items")
        lines.append("")
        lines += [f"- **{speaker}:** {text}" for speaker, text in action_items]
        lines.append("")

    lines.append("## Transcript")
    lines.append("")
    for start, _end, speaker, text, low_confidence in combined:
        marker = " *[uncertain]*" if low_confidence else ""
        lines.append(f"**[{format_time(start)}] {speaker}:**{marker} {text}")

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
    include_topics: bool = True,
    include_mentions: bool = True,
    include_numbers: bool = True,
    include_sentiment: bool = True,
    redact_text: bool = True,
    initial_prompt: str | None = None,
    markdown: bool = False,
    diarize_speakers: bool = False,
    hf_token: str | None = None,
    translate_to: str | None = None,
    translate_from: str = "auto",
) -> None:
    model = load_model(model_size)

    print("Transcribing your audio...")
    mic_segments = transcribe(mic_file, model, initial_prompt=initial_prompt)
    print("Transcribing the other side...")
    speaker_segments = transcribe(speaker_file, model, initial_prompt=initial_prompt)

    diarization_turns = None
    if diarize_speakers:
        if not hf_token:
            print("Skipping diarization: --hf-token (or HF_TOKEN env var) not set.")
        else:
            from diarize import diarize as run_diarization

            print("Diarizing the other side (this needs pyannote.audio + torch)...")
            try:
                diarization_turns = run_diarization(speaker_file, hf_token)
            except RuntimeError as exc:
                print(f"Skipping diarization: {exc}")

    build_doc(
        mic_segments,
        speaker_segments,
        output_file,
        include_summary=include_summary,
        include_action_items=include_action_items,
        include_topics=include_topics,
        include_mentions=include_mentions,
        include_numbers=include_numbers,
        include_sentiment=include_sentiment,
        redact_text=redact_text,
        diarization_turns=diarization_turns,
        translate_to=translate_to,
        translate_from=translate_from,
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
            include_topics=include_topics,
            include_mentions=include_mentions,
            include_numbers=include_numbers,
            include_sentiment=include_sentiment,
            redact_text=redact_text,
            diarization_turns=diarization_turns,
            translate_to=translate_to,
            translate_from=translate_from,
        )
        print(f"Also saved to {md_path}")


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Transcribe a recorded call into a Word document.")
    parser.add_argument("mic_wav", help="Path to the mic recording (.wav)")
    parser.add_argument("speaker_wav", help="Path to the speaker/loopback recording (.wav)")
    parser.add_argument("-o", "--output", default="call_notes.docx", help="Output .docx path")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE, choices=["tiny", "base", "small", "medium", "large-v3"])
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
        "requirements-translate.txt and internet access at translate time.",
    )
    parser.add_argument(
        "--translate-from",
        default="auto",
        metavar="LANG",
        help="Source language code for --translate (default: auto-detect)",
    )
    args = parser.parse_args()

    transcribe_call(
        args.mic_wav,
        args.speaker_wav,
        args.output,
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
        translate_to=args.translate,
        translate_from=args.translate_from,
    )


if __name__ == "__main__":
    main()
