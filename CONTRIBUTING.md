# Contributing

## Setup

```bash
git clone https://github.com/jdtho/call-notes-bot.git
cd call-notes-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
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
  functions (like `merge_segments`, `format_time`, `summarize`) that don't
  touch audio devices or the filesystem.
- Keep dependencies in `requirements.txt` minimal; add dev-only tools to
  `requirements-dev.txt`.
