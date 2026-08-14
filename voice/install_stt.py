#!/usr/bin/env python3
"""Step 2 of the voice-layer setup: install faster-whisper, download a
model, and test it on a real recording. Confirms before installing
anything.

Picked for this setup based on check_env.py's report: no GPU, no C
compiler/make (rules out compiling whisper.cpp on Windows), so
faster-whisper (pure pip, prebuilt CPU wheels) is the right engine.
Default model size is 'base' — a reasonable CPU-only tradeoff; pass
--model tiny if it feels slow, or a bigger size if you have RAM to spare.

Audio I/O uses `soundcard`, not `sounddevice`: on Windows, soundcard
talks to WASAPI directly (ctypes/COM) instead of bundling a prebuilt
native PortAudio binary. sounddevice's bundled ARM64 PortAudio DLL
proved unreliable on this machine (worked once, then consistently
failed to load with error 0x7e even with the matching Visual C++
Redistributable confirmed installed) — soundcard sidesteps that whole
class of problem by not shipping a compiled binary blob at all.
"""

import argparse
import subprocess
import sys
import tempfile
import wave

DEFAULT_MODEL = "base"


def pip_install(*pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])


def record(seconds, samplerate):
    import soundcard as sc

    print(f"Recording for {seconds}s — speak now...")
    mic = sc.default_microphone()
    audio = mic.record(samplerate=samplerate, numframes=int(seconds * samplerate))
    print("Done recording.")
    return audio  # float32 numpy array, shape (n, channels)


def save_wav(path, audio, samplerate):
    import numpy as np

    mono = audio[:, 0] if audio.ndim > 1 else audio
    int16 = np.clip(mono * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(samplerate)
        wf.writeframes(int16.tobytes())


def main():
    ap = argparse.ArgumentParser(description="Install + test local speech-to-text")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                     help="whisper model size: tiny, base, small, medium (default: base)")
    ap.add_argument("--seconds", type=int, default=5, help="test recording length")
    ap.add_argument("--skip-install", action="store_true",
                     help="skip pip install, just run the recording test")
    args = ap.parse_args()

    if not args.skip_install:
        print("This will install (pip): faster-whisper, soundcard, numpy")
        print(f"and download the '{args.model}' Whisper model on first use (one-time, ~size varies by model).")
        print("Nothing else on this machine is touched.")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            print("Aborted — nothing installed.")
            return
        print("Installing...")
        pip_install("faster-whisper", "soundcard", "numpy")

    print(f"\nLoading '{args.model}' model (downloads it on first run)...")
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print("Model loaded.")

    samplerate = 16000
    input(f"\nPress Enter, then speak — recording starts immediately for {args.seconds}s.")
    audio = record(args.seconds, samplerate)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        save_wav(tmp.name, audio, samplerate)
        print("Transcribing...")
        segments, info = model.transcribe(tmp.name)
        text = " ".join(seg.text.strip() for seg in segments)

    print(f"\nDetected language: {info.language} (confidence {info.language_probability:.2f})")
    print(f"Transcript: {text!r}")
    print("\nIf that text matches what you said, step 2 works. Paste this output back.")


if __name__ == "__main__":
    main()
