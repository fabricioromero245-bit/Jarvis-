#!/usr/bin/env python3
"""Step 3 of the voice-layer setup: install Piper (local TTS), download
a voice, and speak a test sentence out loud. Confirms before installing
anything.

Piper over Kokoro: a Piper voice is ~60MB vs. Kokoro's ~350MB, and this
machine has no GPU to make Kokoro's extra quality worth the weight.
Default voice is Spanish (es_ES) since that's the language in use here
— override with --voice if you want a different language/accent.

Playback uses `soundcard`, not `sounddevice`: sounddevice's bundled
ARM64 PortAudio DLL was unreliable on this machine (worked once, then
consistently failed with error 0x7e — confirmed not a missing Visual
C++ Redistributable, that was already installed). soundcard talks to
WASAPI directly via ctypes/COM instead of shipping a compiled binary.
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


def synthesize(model_path, text, out_wav, length_scale=1.0, noise_scale=0.667, noise_w=0.8):
    # Reverted to Piper's own defaults 2026-08-14: pushing noise_scale/
    # noise_w higher to sound more "expressive" instead made it sound
    # worse. Piper's ceiling is architectural, not a tuning problem —
    # see voice/README.md.
    result = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(model_path), "--output_file", str(out_wav),
         "--length_scale", str(length_scale), "--noise_scale", str(noise_scale), "--noise_w", str(noise_w)],
        input=text, text=True, capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("piper synthesis failed — see error above")


def play(wav_path):
    import numpy as np
    import soundcard as sc

    with wave.open(str(wav_path), "rb") as wf:
        samplerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    print("Playing...")
    speaker = sc.default_speaker()
    speaker.play(audio, samplerate=samplerate)


def main():
    ap = argparse.ArgumentParser(description="Install + test local text-to-speech (Piper)")
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                     help="Piper voice name, e.g. es_ES-davefx-medium (default) or en_US-lessac-medium")
    ap.add_argument("--text", default=DEFAULT_TEXT, help="text to speak")
    ap.add_argument("--length-scale", type=float, default=1.0, help="speaking rate, higher = slower (Piper default 1.0)")
    ap.add_argument("--noise-scale", type=float, default=0.667, help="tonal variation (Piper default 0.667)")
    ap.add_argument("--noise-w", type=float, default=0.8, help="pacing variation (Piper default 0.8)")
    ap.add_argument("--skip-install", action="store_true",
                     help="skip pip install, just (re)fetch the voice and speak")
    args = ap.parse_args()

    if not args.skip_install:
        print("This will install (pip): piper-tts, soundcard, numpy")
        print(f"and download the '{args.voice}' voice (~60MB, one-time).")
        print("Nothing else on this machine is touched.")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            print("Aborted — nothing installed.")
            return
        print("Installing...")
        pip_install("piper-tts", "soundcard", "numpy")

    print(f"\nFetching voice '{args.voice}' if not already cached...")
    model_path = ensure_voice(args.voice)

    out_wav = Path(__file__).resolve().parent / "_tts_test.wav"
    print(f"Synthesizing: {args.text!r}")
    synthesize(model_path, args.text, out_wav,
               length_scale=args.length_scale, noise_scale=args.noise_scale, noise_w=args.noise_w)

    play(out_wav)
    print("\nIf you heard that sentence spoken, step 3 works. Paste this output back.")


if __name__ == "__main__":
    main()
