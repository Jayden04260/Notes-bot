# Contributing

## Setup

```bash
git clone https://github.com/Jayden04260/Notes-bot.git
cd Notes-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm   # needed for the Mentioned section
```

## Running checks

```bash
pytest -v
ruff check .
```

Both run in CI on every push and pull request.

## Notes for contributors

- `record_call.py` depends on `soundcard` and Windows WASAPI loopback, so it
  can't be unit tested directly — keep new logic that needs testing in pure
  functions (like `merge_segments`, `format_time`, `summarize`,
  `extract_keywords`, `find_action_items`, `redact`, `extract_entities`,
  `closest_speaker`/`apply_diarization`) that don't touch audio devices,
  the filesystem, or (for diarization) pyannote's actual model.
- Keep dependencies in `requirements.txt` minimal; add dev-only tools to
  `requirements-dev.txt`.
