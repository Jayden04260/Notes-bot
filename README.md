# Call Notes Bot

Record both sides of a call from a Windows laptop, transcribe it locally with
Whisper, and get a speaker-labeled, timestamped Word document with an
auto-generated summary — no cloud transcription service, no data leaving
your machine.

![Tests](https://github.com/Jayden04260/Notes-bot/actions/workflows/tests.yml/badge.svg)
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
- **Auto-detected "Action Items"** — a lightweight rule-based pass flags lines that read like commitments, requests, or deadlines ("I'll...", "can you...", "please...", "by Friday", "due on the 14th"), while ignoring call chatter like "can you hear me?" or "I'm going to be honest" — measured, see [How accurate is it?](#how-accurate-is-it).
- **"Topics" line and "Mentioned" section** — top TF-IDF terms for a quick scan-header, plus people/organizations/dates/places pulled out via spaCy's named-entity recognition.
- **"Numbers Mentioned" table** — money amounts and percentages pulled out via regex into a table (value, type, speaker, context), so figures don't get buried in the transcript.
- **"Tone" summary and "Tense Moments"** — a per-speaker sentiment read (Positive/Neutral/Negative) via [VADER](https://github.com/cjhutto/vaderSentiment), plus the most negative-scoring lines surfaced separately. Lexicon-based and English-tuned, so treat it as a rough pointer to skim, not a verdict — short informal lines and sarcasm can mis-score.
- **Redaction** of numbers that look like credit cards (Luhn-checked) or US SSNs, on by default.
- **Whisper hallucination filtering** — segments Whisper is essentially certain are silence/noise are dropped; segments it's merely unsure about are kept but marked *[uncertain]* so you know to double-check that line instead of silently losing it.
- **Vocabulary biasing** via `--prompt` (faster-whisper's `initial_prompt`) for names/jargon that come up on your calls.
- **GPU transcription** — on an NVIDIA GPU (with `requirements-gpu.txt`), transcription runs ~8x faster and defaults to Whisper `large-v3-turbo`: ~40% fewer word errors than the CPU default. Falls back to CPU automatically. See [How accurate is it?](#how-accurate-is-it).
- **Configurable accuracy/speed tradeoff** via `--model auto|tiny|base|small|medium|large-v3|large-v3-turbo` and `--device auto|cuda|cpu`.
- **Non-English calls** via `--language <code>` or `--language auto` (default: English).
- **Optional transcript translation** to (or from) any language Google Translate supports, via `--translate`.
- Unit-tested core logic, CI on every push.

## Install

```bash
git clone https://github.com/Jayden04260/Notes-bot.git
cd Notes-bot
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # needed for the Mentioned section
```

Requires Python 3.10+ and Windows (uses WASAPI loopback for system-audio capture).

### GPU transcription (optional, recommended with an NVIDIA GPU)

```bash
pip install -r requirements-gpu.txt
```

This adds NVIDIA's cuBLAS/cuDNN libraries as pip packages - no system-wide
CUDA install needed (`gpu.py` makes them findable on Windows). `run.bat`
installs them automatically when it finds an NVIDIA GPU. With them
installed, `--device auto` (the default) runs Whisper on the GPU and
`--model auto` picks `large-v3-turbo`; without, everything runs on the CPU
exactly as before. If the GPU can't be used for any reason, Notes-bot says
why and falls back to the CPU rather than failing the run.

The first run on a GPU takes ~30s longer while the GPU is prepared
(on GPUs newer than the installed CTranslate2 build, kernels are compiled
on first use) - later runs start straight away.

If `spacy download` fails with a certificate error (common behind
antivirus or corporate proxies that inspect HTTPS), use the OS certificate
store instead: `python -c "import truststore; truststore.inject_into_ssl(); from spacy.cli import download; download('en_core_web_sm')"`
(this is what `run.bat` does).

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
python run.py --model large-v3      # pick a model explicitly (default: auto - see GPU transcription)
python run.py --device cpu          # force CPU even if a GPU is available
python run.py --language auto       # detect the call's language instead of assuming English
python run.py --no-summary          # skip the Key Points section
python run.py --no-action-items     # skip the Action Items section
python run.py --no-topics           # skip the Topics line
python run.py --no-mentions         # skip the Mentioned (people/orgs/dates) section
python run.py --no-numbers          # skip the Numbers Mentioned (money/percentages) table
python run.py --no-sentiment        # skip the Tone summary and Tense Moments section
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
Tone: Them — Negative, You — Neutral

Key Points
  • The launch date was moved to the 14th because of the vendor delay.
  • Budget sign-off still needs to come from finance before Friday.

Mentioned
  • People: Sarah
  • Organizations: Acme Corp
  • Dates: Friday, the 14th

Numbers Mentioned
  | Value  | Type       | Speaker | Context                                  |
  | ------ | ---------- | ------- | ----------------------------------------- |
  | $12,000| Money      | Them    | The budget's capped at $12,000 for this.  |
  | 15%    | Percentage | You     | We're already 15% over on the timeline.   |

Tense Moments
  • Them: This budget cut is completely unacceptable and honestly infuriating.

Action Items
  • Them: I'll get budget sign-off from finance by Friday.
  • You: Can you send over the updated timeline tomorrow?

Transcript
  [00:03] Them: So the main thing we need to figure out is timeline.
  [00:07] You:  Right, I think we can commit to end of next month.
  [00:15] Them: Okay, and budget sign-off — where's that at?
```

## How accurate is it?

Two evaluation scripts measure the parts that can be measured offline.

**Transcription** (`eval_transcription.py`): word error rate on the 73-clip
LibriSpeech sample from `hf-internal-testing/librispeech_asr_dummy` (8 minutes
of clean read speech, with reference transcripts), on an RTX 5080 laptop GPU
/ the same laptop's CPU:

| Model | Device | Word error rate | Speed |
|---|---|---|---|
| small (previous default) | CPU (int8) | 7.1% | 3.7x real-time |
| small | GPU (fp16) | 7.5% | 27.9x real-time |
| **large-v3-turbo** (default with a GPU) | GPU (fp16) | **4.2%** | **29.6x real-time** |
| large-v3 | GPU (fp16) | 4.4% | 13.9x real-time |

So with a GPU, an hour-long call transcribes in about two minutes instead of
~16, with ~40% fewer word errors. `large-v3-turbo` beats full `large-v3` here
at twice the speed. The WER normalisation is deliberately simple (lowercase,
no punctuation), so "Mr." vs a reference's "MISTER" counts as an error - the
absolute numbers are a little pessimistic, the comparison between rows is
what matters. Clean read speech is also easier than a real call: expect
higher error rates on crosstalk, accents, and poor connections.

```bash
python eval_transcription.py path/to/clips --model large-v3-turbo --device cuda
```

**Action items** (`eval_action_items.py`): precision/recall on hand-labelled
call lines (`eval/action_items_labeled.json`). The rules were tuned on the
`dev` split; the `heldout` split was written at the same time but only
scored afterwards, so it's the honest number:

| Rules | Held-out precision | Held-out recall | Held-out F1 |
|---|---|---|---|
| Previous keyword list | 0.40 | 0.50 | 0.44 |
| **Current rules** | **0.75** | **1.00** | **0.86** |

The old list flagged anything containing "going to", "can you", "need to" -
so "I'm going to be honest", "Can you hear me?" and "It's going to rain" were
all action items, and it missed "Please send...", "Would you mind..." and
"due on the 14th" entirely. Still wrong on held-out: set phrases the rules
haven't been told about ("I need to tell you...", "Could you imagine...",
"I will admit..."). 64 lines written by one person is a sanity check, not a
benchmark.

```bash
python eval_action_items.py
```

## Testing

```bash
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
pytest -v
```

Tests cover the pure-logic pieces (segment merging, timestamp formatting, model
selection, WER maths, diarization output handling,
summarization, entity extraction, numeric mention extraction, sentiment
scoring) — the parts that don't require a live mic/speaker or a downloaded
Whisper model, so they run fast and in CI.

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
- Transcription defaults to English; `--language <code>` or `--language auto`
  handles other languages, but Key Points, Action Items, Topics, Mentioned and
  Tone are English-tuned (use `--translate en` to get those on an English
  copy).
- Without a GPU the default model is `small` (7.1% WER, ~3.7x real-time on
  CPU); use `--model tiny` or `--model base` for faster turnaround at the cost
  of accuracy.
- CI can't test `record_call.py` (soundcard needs an audio server the CI
  runners don't have), so audio-capture regressions are only caught by
  running it.

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
Mentioned, Numbers Mentioned, Tone/Tense Moments, and Action Items are still
computed from the original-language text, since the summarizer/entity-
extraction/numeric-mentions/sentiment/action-item logic is English-tuned.
It needs internet access at translate time. `run.bat`
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
      works with pyannote.audio 3.x and 4.x, but not verified against a real
      recording, since it needs your own Hugging Face token for the gated model)
- [x] GPU transcription with automatic model choice and CPU fallback
- [x] Measured transcription and action-item accuracy (see "How accurate is it?")
- [x] Action-item extraction alongside the Key Points summary
- [x] Optional transcript translation (see above)

## License

All Rights Reserved — this repository is public for portfolio/demonstration
purposes only; no reuse, modification, or redistribution is licensed. See
[LICENSE](LICENSE).
