"""
diarize.py

Optional group-call speaker diarization for the "Them" (loopback) track,
splitting one lumped "Them" label into distinct external speakers
("Them (SPEAKER_00)", "Them (SPEAKER_01)", ...) via pyannote.audio.

This is intentionally NOT in requirements.txt - see requirements-diarize.txt
and the README's diarization section for setup. It needs:
  1. `pip install -r requirements-diarize.txt` (pulls in torch - a large,
     slow install).
  2. Accepting pyannote/speaker-diarization-3.1's license on Hugging Face
     and generating an access token (huggingface.co/settings/tokens).

`diarize()` only imports pyannote.audio inside the function body, so the
rest of the app has no hard dependency on it and importing this module is
always cheap.
"""

from pathlib import Path

Turn = tuple[float, float, str]

DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"


def diarize(file_path: str | Path, hf_token: str) -> list[Turn]:
    """
    Run speaker diarization on a wav file, return a list of
    (start, end, speaker_label) tuples, e.g. speaker_label "SPEAKER_00".
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Diarization needs extra dependencies: pip install -r requirements-diarize.txt"
        ) from exc

    # pyannote.audio 4 renamed use_auth_token -> token (and from_pretrained
    # takes no **kwargs, so the old name raises TypeError). Try the current
    # name first so both 3.x and 4.x installs work.
    try:
        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, token=hf_token)
    except TypeError:
        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=hf_token)
    if pipeline is None:  # pyannote returns None (after logging) when the gated model's terms weren't accepted
        raise RuntimeError(
            f"Couldn't load {DIARIZATION_MODEL} - accept its terms at https://huggingface.co/{DIARIZATION_MODEL} "
            "with the account your token belongs to."
        )

    annotation = annotation_from(pipeline(str(file_path)))
    return [(turn.start, turn.end, label) for turn, _, label in annotation.itertracks(yield_label=True)]


def annotation_from(output):
    """The speaker timeline from a pipeline result, across pyannote versions.

    3.x returns the timeline (an Annotation) directly. 4.x returns a
    DiarizeOutput wrapping two: `speaker_diarization`, and
    `exclusive_speaker_diarization` - the same turns with overlapping speech
    resolved to one speaker at a time, which pyannote provides specifically
    for aligning with transcripts (what apply_diarization() does), so it's
    preferred when present.
    """
    for attr in ("exclusive_speaker_diarization", "speaker_diarization"):
        annotation = getattr(output, attr, None)
        if annotation is not None:
            return annotation
    return output


def closest_speaker(segment_start: float, segment_end: float, turns: list[Turn]) -> str | None:
    """
    Given a transcript segment's (start, end) and a list of diarization
    turns, return the turn's speaker label with the greatest time overlap,
    or None if no turn overlaps at all. Pure function - no I/O - so it's
    easy to unit test without pyannote installed.
    """
    best_label = None
    best_overlap = 0.0
    for turn_start, turn_end, label in turns:
        overlap = min(segment_end, turn_end) - max(segment_start, turn_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = label
    return best_label


def apply_diarization(
    combined: list[tuple[float, float, str, str, bool]], turns: list[Turn]
) -> list[tuple[float, float, str, str, bool]]:
    """
    Relabel "Them" rows in a merged transcript (start, end, speaker, text,
    low_confidence) with the diarized speaker that overlaps them most, e.g.
    "Them" -> "Them (SPEAKER_01)". Rows with no overlapping turn, and "You"
    rows, are left unchanged. Pure function - easy to unit test.
    """
    result = []
    for start, end, speaker, text, low_confidence in combined:
        if speaker == "Them":
            label = closest_speaker(start, end, turns)
            if label is not None:
                speaker = f"Them ({label})"
        result.append((start, end, speaker, text, low_confidence))
    return result
