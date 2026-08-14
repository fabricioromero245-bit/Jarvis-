#!/usr/bin/env python3
"""Step 4 of the voice-layer setup: push-to-talk daemon.

Hold the key, speak, release — runs the full loop: mic (soundcard) ->
STT (faster-whisper) -> `claude -p` -> TTS (Piper) -> speakers, and
keeps voice/state.json updated live so the HUD's Audio I/O panel
reflects mic/speaker state and the last transcript in real time.

Default hotkey is right Ctrl — the standard push-to-talk convention
(same as Discord etc.), chosen because F9 (the original default)
turned out to collide with Edge's own "Reading mode" shortcut when the
orb window (gui/) has focus. Override with --key if it collides with
anything on your setup. Requires the `claude` CLI on PATH; if it isn't,
the loop still records/transcribes/speaks, it just reports the
claude-call error instead of a response — see voice/README.md.
"""

import argparse
import queue
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from pathlib import Path

import voice_lib as vl

DEFAULT_KEY = "ctrl_r"
DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "es"
DEFAULT_VOICE = "es_ES-davefx-medium"
HEARTBEAT_SECONDS = 5
RECORD_CHUNK_FRAMES = 4096  # larger chunk = fewer, steadier reads (1024 caused discontinuity warnings)

# Each `claude -p` call is a fresh, memoryless conversation — nothing
# carries over turn to turn (a real limitation, not just a language
# quirk; see voice/README.md). Short/ambiguous input can make it reply
# in the wrong language with no prior turn to anchor it, so the spoken
# language is pinned explicitly per call instead of left to guesswork.
LANGUAGE_NAMES = {"es": "Spanish", "en": "English", "pt": "Portuguese", "fr": "French"}

# soundcard warns on minor buffer discontinuities; harmless in practice
# here (confirmed on 2026-08-14: recording still transcribed correctly),
# just noisy — filtered instead of silently swallowing real errors.
warnings.filterwarnings("ignore", message="data discontinuity in recording")


def pip_install(*pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *pkgs])


def parse_key(name, keyboard):
    name = name.lower()
    special = getattr(keyboard.Key, name, None)
    if special is not None:
        return special
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unrecognized key: {name!r}")


def main():
    ap = argparse.ArgumentParser(description="Push-to-talk voice loop")
    ap.add_argument("--key", default=DEFAULT_KEY, help="hotkey to hold (default: ctrl_r, i.e. right Ctrl)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="whisper model size")
    ap.add_argument("--language", default=DEFAULT_LANGUAGE, help="STT language, '' for auto-detect")
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                     help="Piper voice name, e.g. es_ES-davefx-medium (default) or es_MX-ald-medium")
    ap.add_argument("--samplerate", type=int, default=16000)
    ap.add_argument("--length-scale", type=float, default=1.0, help="speaking rate, higher = slower (Piper default 1.0)")
    ap.add_argument("--noise-scale", type=float, default=0.667, help="tonal variation (Piper default 0.667; pushing this higher made it worse, not better, on 2026-08-14's test)")
    ap.add_argument("--noise-w", type=float, default=0.8, help="pacing variation (Piper default 0.8)")
    ap.add_argument("--skip-install", action="store_true", help="skip pip install of pynput")
    args = ap.parse_args()

    if not args.skip_install:
        print("This will install (pip): pynput")
        print("(faster-whisper, soundcard, piper-tts should already be installed from steps 2-3)")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            print("Aborted — nothing installed.")
            return
        pip_install("pynput")

    from pynput import keyboard
    import numpy as np
    import soundcard as sc

    target_key = parse_key(args.key, keyboard)
    voice_model = vl.MODELS_DIR / f"{args.voice}.onnx"
    if not voice_model.exists():
        print(f"Voice model not found: {voice_model}")
        print("Run install_tts.py first (step 3) to download it.")
        sys.exit(1)

    print(f"Loading STT model ('{args.model}')...")
    model = vl.load_stt_model(args.model)
    print("Ready.")

    pressed = threading.Event()
    audio_queue = queue.Queue()

    def on_press(key):
        if key == target_key and not pressed.is_set():
            pressed.set()

    def on_release(key):
        if key == target_key:
            pressed.clear()

    keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True).start()

    def recorder_loop():
        mic = sc.default_microphone()
        while True:
            pressed.wait()
            vl.write_state(mic="listening", speaker="idle")
            frames = []
            with mic.recorder(samplerate=args.samplerate) as rec:
                while pressed.is_set():
                    frames.append(rec.record(numframes=RECORD_CHUNK_FRAMES))
            if frames:
                audio_queue.put(np.concatenate(frames, axis=0))
            else:
                vl.write_state(mic="idle", speaker="idle", note=f"hold {args.key} to talk")

    threading.Thread(target=recorder_loop, daemon=True).start()

    def heartbeat_loop():
        while True:
            time.sleep(HEARTBEAT_SECONDS)
            if not pressed.is_set() and audio_queue.empty():
                vl.write_state(mic="idle", speaker="idle", note=f"hold {args.key} to talk")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    vl.write_state(mic="idle", speaker="idle", note=f"hold {args.key} to talk")
    print(f"\nHold {args.key.upper()} to talk. Ctrl+C to quit.")

    while True:
        audio = audio_queue.get()
        mono = audio[:, 0] if audio.ndim > 1 else audio

        vl.write_state(mic="processing", speaker="idle")
        text = vl.transcribe(model, mono, language=args.language)
        if not text:
            print("(heard nothing)")
            vl.write_state(mic="idle", speaker="idle", note=f"hold {args.key} to talk")
            continue

        print(f"\nYou: {text}")
        vl.write_state(mic="idle", speaker="idle", last_transcript=text, note="thinking...")

        prompt = text
        if args.language:
            lang_name = LANGUAGE_NAMES.get(args.language, args.language)
            prompt = f"(Respond only in {lang_name}.) {text}"

        try:
            response = vl.ask_claude(prompt)
        except RuntimeError as e:
            print(f"claude error: {e}")
            vl.write_state(mic="idle", speaker="idle", last_transcript=text, note=str(e))
            continue

        print(f"Claude: {response}")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            try:
                vl.synthesize(voice_model, response, tmp.name,
                              length_scale=args.length_scale, noise_scale=args.noise_scale, noise_w=args.noise_w)
                vl.write_state(mic="idle", speaker="speaking", last_transcript=text)
                vl.play_wav(tmp.name)
            except RuntimeError as e:
                print(f"tts error: {e}")

        vl.write_state(mic="idle", speaker="idle", last_transcript=text, note=f"hold {args.key} to talk")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        vl.write_state(mic="offline", speaker="offline", note="stopped")
