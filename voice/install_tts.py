#!/usr/bin/env python3
"""Step 3 of the voice-layer setup: install Piper (local TTS), download
a voice, and speak a test sentence out loud. Confirms before installing
anything.

Piper over Kokoro: a Piper voice is ~60MB vs. Kokoro's ~350MB, and this
machine has no GPU to make Kokoro's extra quality worth the weight.
Default voice is Spanish (es_ES) since that's the language in use here
— override with --voice if you want a different language/accent.
"""

import argparse
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
DEFAULT_VOICE = "es_ES-davefx-medium"
DEFAULT_TEXT = "Hola, este es Jarvis probando la voz."


def voice_url(voice, ext):
    # voice looks like "es_ES-davefx-medium" -> lang=es, region-name=es_ES,
    # name=davefx, quality=medium
    lang_region, name, quality = voice.split("-")
    lang = lang_region.split("_")[0]
    return (f"https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            f"{lang}/{lang_region}/{name}/{quality}/{voice}{ext}")


def pip_install(*pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])


def download(url, dest):
    print(f"  downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest)


def ensure_voice(voice):
    MODELS_DIR.mkdir(exist_ok=True)
    onnx_path = MODELS_DIR / f"{voice}.onnx"
    json_path = MODELS_DIR / f"{voice}.onnx.json"
    if not onnx_path.exists():
        download(voice_url(voice, ".onnx"), onnx_path)
    if not json_path.exists():
        download(voice_url(voice, ".onnx.json"), json_path)
    return onnx_path


def synthesize(model_path, text, out_wav):
    result = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(model_path), "--output_file", str(out_wav)],
        input=text, text=True, capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("piper synthesis failed — see error above")


def play(wav_path):
    import numpy as np
    import sounddevice as sd

    with wave.open(str(wav_path), "rb") as wf:
        samplerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
    print("Playing...")
    sd.play(audio, samplerate)
    sd.wait()


def main():
    ap = argparse.ArgumentParser(description="Install + test local text-to-speech (Piper)")
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                     help="Piper voice name, e.g. es_ES-davefx-medium (default) or en_US-lessac-medium")
    ap.add_argument("--text", default=DEFAULT_TEXT, help="text to speak")
    ap.add_argument("--skip-install", action="store_true",
                     help="skip pip install, just (re)fetch the voice and speak")
    args = ap.parse_args()

    if not args.skip_install:
        print("This will install (pip): piper-tts")
        print(f"and download the '{args.voice}' voice (~60MB, one-time).")
        print("Nothing else on this machine is touched.")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            print("Aborted — nothing installed.")
            return
        print("Installing...")
        pip_install("piper-tts")

    print(f"\nFetching voice '{args.voice}' if not already cached...")
    model_path = ensure_voice(args.voice)

    out_wav = Path(__file__).resolve().parent / "_tts_test.wav"
    print(f"Synthesizing: {args.text!r}")
    synthesize(model_path, args.text, out_wav)

    play(out_wav)
    print("\nIf you heard that sentence spoken, step 3 works. Paste this output back.")


if __name__ == "__main__":
    main()
