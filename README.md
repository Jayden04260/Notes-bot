# Call Notes Bot

Record both sides of a call from a Windows laptop, transcribe it locally with
Whisper, and get a speaker-labeled, timestamped Word document with an
auto-generated summary — no cloud transcription service, no data leaving
your machine.

![Tests](https://github.com/jdtho/call-notes-bot/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Why

Meeting notes are annoying to take by hand and cloud transcription tools
mean sending call audio to a third party. This runs entirely on-device:
audio capture, speech-to-text, and summarization all happen locally.

## How it works

```
                 ┌─────────────────┐
  Your mic  ───▶ │                 │
                 │  record_call.py │──▶ mic.wav
  Speaker   ───▶ │  (WASAPI        │
  loopback       │   loopback)     │──▶ speaker.wav
                 └─────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │ transcribe_to_word.py  │
              │  Whisper (local STT)   │
              └────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │     summarize.py       │
              │  TF-IDF + TextRank-    │
              │  style extractive      │
              │  summarization         │
              └────────────────────────┘
                          │
                          ▼
                  call_notes.docx
           (Key Points + full transcript)
```

Speaker separation works because during any call app (Teams, Zoom, Meet,
phone-via-Bluetooth), the other person's voice plays out through your
speakers while your voice only goes into your mic — so capturing both
tracks separately gives a cheap, reliable way to label "You" vs. "Them"
without needing voice-based diarization.

## Features

- **Fully local** — speech-to-text via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), summarization via scikit-learn. No API keys, no audio uploaded anywhere.
- **Speaker-labeled, timestamped transcript** in a clean Word document (optionally also Markdown, via `--markdown`).
- **Auto-generated "Key Points" summary** using a from-scratch TextRank-style extractive summarizer (TF-IDF + sentence-similarity graph ranking, picked via Maximal Marginal Relevance so the summary doesn't fill up with near-duplicate lines) — not just a call to an LLM API.
- **Auto-detected "Action Items"** — a lightweight rule-based pass flags lines that read like commitments, requests, or deadlines ("I'll...", "can you...", "by Friday").
- **Redaction** of numbers that look like credit cards (Luhn-checked) or US SSNs, on by default.
- **Whisper hallucination filtering** — segments with low confidence or high no-speech probability are dropped before they hit the transcript.
- **Vocabulary biasing** via `--prompt` (faster-whisper's `initial_prompt`) for names/jargon that come up on your calls.
- **Configurable accuracy/speed tradeoff** via `--model tiny|base|small|medium|large-v3`.
- Unit-tested core logic, CI on every push.

## Install

```bash
git clone https://github.com/jdtho/call-notes-bot.git
cd call-notes-bot
pip install -r requirements.txt
```

Requires Python 3.10+ and Windows (uses WASAPI loopback for system-audio capture).

## Usage

```bash
python run.py
```

Or double-click `run.bat` (creates a `.venv` and installs dependencies on
first run if one doesn't exist yet). To launch it from the Desktop or Start
Menu, make a shortcut pointing at `run.bat` with "Start in" set to this
folder.

- Prints the detected mic and speaker device.
- Records until you press **Enter**.
- Transcribes both tracks locally and writes `recordings/call_notes_<timestamp>.docx`.

Options:

```bash
python run.py --model base          # more accurate, slower, more memory
python run.py --no-summary          # skip the Key Points section
python run.py --no-action-items     # skip the Action Items section
python run.py --no-redact           # don't redact card/SSN-looking numbers
python run.py --markdown            # also write a .md alongside the .docx
python run.py --prompt "Acme, Jordan, Q3 roadmap"   # bias Whisper's vocabulary
```

Or run transcription on an existing pair of recordings directly:

```bash
python transcribe_to_word.py recordings/mic_x.wav recordings/speaker_x.wav -o notes.docx
```

## Example output

```
Key Points
  • The launch date was moved to the 14th because of the vendor delay.
  • Budget sign-off still needs to come from finance before Friday.

Action Items
  • Them: I'll get budget sign-off from finance by Friday.
  • You: Can you send over the updated timeline tomorrow?

Transcript
  [00:03] Them: So the main thing we need to figure out is timeline.
  [00:07] You:  Right, I think we can commit to end of next month.
  [00:15] Them: Okay, and budget sign-off — where's that at?
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests cover the pure-logic pieces (segment merging, timestamp formatting,
summarization) — the parts that don't require a live mic/speaker or a
downloaded Whisper model, so they run fast and in CI.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .     # lint
pytest -v        # tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more.

## Limitations

- Windows-only as written (WASAPI loopback). A Mac/Linux port would swap
  the loopback capture method in `record_call.py`.
- Speaker labels are per-audio-track ("You" vs "Them"), not true
  voice-based diarization — fine for 1:1 calls, less precise if multiple
  people are on the other end.
- Summarization is extractive (it selects real sentences from the
  transcript), not abstractive — it won't paraphrase, only pick out the
  most representative lines.

## Consent

Recording calls has legal requirements in many places — some jurisdictions
require everyone on the call to consent before recording. Check what
applies to you and the other party before using this on a real call.

## Roadmap

- [ ] Live/streaming transcription instead of record-then-transcribe
- [ ] Cross-platform audio capture (macOS/Linux)
- [ ] True voice-based diarization for group calls (would add `pyannote.audio`
      + `torch` and require a Hugging Face token for the gated model — a
      real dependency/privacy-story tradeoff against staying "no API keys")
- [x] Action-item extraction alongside the Key Points summary

## License

MIT — see [LICENSE](LICENSE).
