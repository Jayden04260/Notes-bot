"""
record_call.py

Records two audio tracks at once during a call:
  - your microphone (what YOU say)
  - your speaker output via WASAPI loopback (what THEY say, since their
    voice plays out of your speakers/headphones during any call app)

Press Enter to stop recording. Files are saved under ./recordings/
"""

# Keeps the `sc.Microphone` annotation below from being evaluated at import
# time: soundcard 0.4.6 no longer exports a top-level Microphone class, and
# evaluating the hint made `python run.py` crash before recording anything.
from __future__ import annotations

import threading
import time
import wave
from pathlib import Path

import numpy as np
import soundcard as sc

SAMPLE_RATE = 16000  # good enough for speech, keeps files small


def record_stream(
    mic: sc.Microphone,
    filename: Path,
    stop_event: threading.Event,
    start_barrier: threading.Barrier,
    errors: list[BaseException],
    samplerate: int = SAMPLE_RATE,
) -> None:
    # Runs in a background thread, so an unhandled exception here would
    # otherwise just print to stderr and vanish - the main thread would
    # carry on and hand back a file path that was never actually written,
    # then fail confusingly much later inside Whisper instead of here with
    # a clear cause. `errors` lets the main thread find out and stop.
    frames = []
    chunk = samplerate // 10  # ~100ms chunks - pulling smaller/more frequent
    # chunks keeps soundcard's internal buffer from overflowing, which is
    # what causes "data discontinuity in recording" warnings
    try:
        with mic.recorder(samplerate=samplerate, blocksize=chunk) as rec:
            # Opening a WASAPI device (above) has variable latency that
            # differs between the mic and the loopback speaker device. If
            # each thread started pulling frames as soon as its own device
            # opened, "frame 0" in the two files wouldn't line up with the
            # same wall-clock instant, which would throw off Whisper's
            # timestamps and the merged transcript's ordering. Waiting here
            # until both devices are open keeps the two tracks in sync.
            start_barrier.wait()
            while not stop_event.is_set():
                data = rec.record(numframes=chunk)
                frames.append(data)
    except threading.BrokenBarrierError:
        # The other track's device failed to open before reaching this
        # point (see the `except Exception` branch below, on that thread) -
        # it already recorded the real error, there's nothing to add here.
        return
    except Exception as exc:
        errors.append(exc)
        stop_event.set()
        start_barrier.abort()  # release the other thread if it's still waiting, instead of hanging forever
        return
    if frames:
        audio = np.concatenate(frames, axis=0)
        write_wav(filename, audio, samplerate)


def write_wav(filename: Path, audio: np.ndarray, samplerate: int) -> None:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # downmix to mono
    audio_int16 = np.int16(np.clip(audio, -1, 1) * 32767)
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio_int16.tobytes())


def record_call() -> tuple[Path, Path]:
    out_dir = Path("recordings")
    out_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    mic_file = out_dir / f"mic_{timestamp}.wav"
    speaker_file = out_dir / f"speaker_{timestamp}.wav"

    try:
        default_mic = sc.default_microphone()
        default_speaker = sc.default_speaker()
        # include_loopback=True on a speaker id gives you a "microphone" object
        # that actually captures what's playing out of that speaker
        loopback_mic = sc.get_microphone(id=str(default_speaker.name), include_loopback=True)
    except RuntimeError as exc:
        raise RuntimeError(
            "Could not find a default microphone/speaker. Check that a mic and "
            "an output device are connected and set as defaults in Windows sound "
            "settings."
        ) from exc

    stop_event = threading.Event()
    start_barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    mic_thread = threading.Thread(
        target=record_stream, args=(default_mic, mic_file, stop_event, start_barrier, errors)
    )
    speaker_thread = threading.Thread(
        target=record_stream, args=(loopback_mic, speaker_file, stop_event, start_barrier, errors)
    )

    print(f"Mic: {default_mic.name}")
    print(f"Speaker (loopback): {default_speaker.name}")
    print("\nRecording... press Enter to stop.")

    mic_thread.start()
    speaker_thread.start()

    input()
    stop_event.set()
    mic_thread.join()
    speaker_thread.join()

    if errors:
        raise RuntimeError(f"Recording failed: {errors[0]}") from errors[0]
    if not mic_file.exists() or not speaker_file.exists():
        raise RuntimeError(
            "Recording produced no audio - a device may have disconnected mid-call. Nothing was saved."
        )

    print(f"\nSaved:\n  {mic_file}\n  {speaker_file}")
    return mic_file, speaker_file


if __name__ == "__main__":
    record_call()
