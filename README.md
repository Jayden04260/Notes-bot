# Call Notes Bot

Record both sides of a call from a Windows laptop, transcribe it locally with
Whisper, and get a speaker-labeled, timestamped Word document with an
auto-generated summary — no cloud transcription service, no data leaving
your machine.

![Tests](https://github.com/jdtho/call-notes-bot/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-lightgrey)

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
- **"Topics" line and "Mentioned" section** — top TF-IDF terms for a quick scan-header, plus people/organizations/dates/places pulled out via spaCy's named-entity recognition.
- **Redaction** of numbers that look like credit cards (Luhn-checked) or US SSNs, on by default.
- **Whisper hallucination filtering** — segments Whisper is essentially certain are silence/noise are dropped; segments it's merely unsure about are kept but marked *[uncertain]* so you know to double-check that line instead of silently losing it.
- **Vocabulary biasing** via `--prompt` (faster-whisper's `initial_prompt`) for names/jargon that come up on your calls.
- **Configurable accuracy/speed tradeoff** via `--model tiny|base|small|medium|large-v3`.
- **Optional transcript translation** to (or from) any language Google Translate supports, via `--translate`.
- Unit-tested core logic, CI on every push.

## Install

```bash
git clone https://github.com/jdtho/call-notes-bot.git
cd call-notes-bot
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # needed for the Mentioned section
```

Requires Python 3.10+ and Windows (uses WASAPI loopback for system-audio capture).

## Usage

```bash
python run.py
```

Or double-click `run.bat` (creates a `.venv` and installs dependencies,
including the optional translation dependency, on first run if one doesn't
exist yet). To launch it from the Desktop or Start Menu, make a shortcut
pointing at `run.bat` with "Start in" set to this folder.

- Prints the detected mic and speaker device.
- Records until you press **Enter**.
- Transcribes both tracks locally and writes `recordings/call_notes_<timestamp>.docx`.

Options:

```bash
python run.py --model base          # more accurate, slower, more memory
python run.py --no-summary          # skip the Key Points section
python run.py --no-action-items     # skip the Action Items section
python run.py --no-topics           # skip the Topics line
python run.py --no-mentions         # skip the Mentioned (people/orgs/dates) section
python run.py --no-redact           # don't redact card/SSN-looking numbers
python run.py --markdown            # also write a .md alongside the .docx
python run.py --prompt "Acme, Jordan, Q3 roadmap"   # bias Whisper's vocabulary
python run.py --translate es                        # translate the transcript to Spanish
```

Or run transcription on an existing pair of recordings directly:

```bash
python transcribe_to_word.py recordings/mic_x.wav recordings/speaker_x.wav -o notes.docx
```

## Example output

```
Topics: budget, timeline, vendor, sign-off, launch

Key Points
  • The launch date was moved to the 14th because of the vendor delay.
  • Budget sign-off still needs to come from finance before Friday.

Mentioned
  • People: Sarah
  • Organizations: Acme Corp
  • Dates: Friday, the 14th

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
python -m spacy download en_core_web_sm
pytest -v
```

Tests cover the pure-logic pieces (segment merging, timestamp formatting,
summarization, entity extraction) — the parts that don't require a live
mic/speaker or a downloaded Whisper model, so they run fast and in CI.

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
- Speaker labels are per-audio-track ("You" vs "Them") by default, not true
  voice-based diarization — fine for 1:1 calls. For group calls, optional
  diarization (see below) can split "Them" into distinct speakers.
- Summarization is extractive (it selects real sentences from the
  transcript), not abstractive — it won't paraphrase, only pick out the
  most representative lines.
- Transcription is hardcoded to English (`language="en"`) for accuracy and
  speed — non-English calls won't transcribe correctly.
- Default model is `small` for better accuracy; use `--model tiny` or
  `--model base` if you want faster turnaround at the cost of accuracy.

## Optional: group-call diarization

For calls with more than one person on the other end, `--diarize` splits the
generic "Them" label into distinct speakers ("Them (SPEAKER_00)",
"Them (SPEAKER_01)", ...) using [pyannote.audio](https://github.com/pyannote/pyannote-audio).
This is opt-in and kept out of the default install because it pulls in
`torch` (a large, slow download) and needs a gated model:

```bash
pip install -r requirements-diarize.txt
```

1. Accept the license for
   [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   on Hugging Face (needs a free account).
2. Generate an access token at
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
3. Run with `--diarize --hf-token <your token>`, or set an `HF_TOKEN`
   environment variable and just pass `--diarize`.

```bash
python run.py --diarize --hf-token hf_xxx
```

Only the "Them" (loopback) track is diarized — your own "You" track is
still identified via the mic, same as always.

## Optional: transcript translation

`--translate <lang>` translates the displayed transcript into another
language after everything else has been generated — Key Points, Topics,
Mentioned, and Action Items are still computed from the original-language
text, since the summarizer/entity-extraction/action-item logic is
English-tuned. It needs internet access at translate time. `run.bat`
installs the dependency for you automatically; if you're running
`python run.py` directly instead, install it once with:

```bash
pip install -r requirements-translate.txt
```

```bash
python run.py --translate es                        # -> Spanish, auto-detected source
python run.py --translate en --translate-from es     # Spanish call -> English transcript
```

Uses [deep-translator](https://github.com/nidhaloff/deep-translator)'s free
Google Translate backend. If a line fails to translate (e.g. no network),
it's kept in the original language rather than dropped.

## Consent

Recording calls has legal requirements in many places — some jurisdictions
require everyone on the call to consent before recording. Check what
applies to you and the other party before using this on a real call.

## Roadmap

- [ ] Live/streaming transcription instead of record-then-transcribe
- [ ] Cross-platform audio capture (macOS/Linux)
- [x] True voice-based diarization for group calls (optional, see above —
      not verified against a real recording, since it needs your own
      Hugging Face token for the gated model)
- [x] Action-item extraction alongside the Key Points summary
- [x] Optional transcript translation (see above)

## License

All Rights Reserved — this repository is public for portfolio/demonstration
purposes only; no reuse, modification, or redistribution is licensed. See
[LICENSE](LICENSE).
