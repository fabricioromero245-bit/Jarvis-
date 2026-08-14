"""Shared runtime helpers for the voice layer: STT, TTS, audio I/O, and
the state file the HUD reads. No install/confirm prompts here — see
install_stt.py / install_tts.py for that; this module is imported by
the push-to-talk daemon (ptt.py) once everything is already installed.
"""

import datetime
import json
import subprocess
import sys
import wave
from pathlib import Path

VOICE_DIR = Path(__file__).resolve().parent
STATE_PATH = VOICE_DIR / "state.json"
MODELS_DIR = VOICE_DIR / "models"


def write_state(mic="idle", speaker="idle", last_transcript=None, note=None):
    state = {
        "mic": mic,
        "speaker": speaker,
        "updated": datetime.datetime.now().isoformat(),
    }
    if last_transcript is not None:
        state["last_transcript"] = last_transcript
    if note is not None:
        state["note"] = note
    STATE_PATH.write_text(json.dumps(state))


def load_stt_model(model_size="base"):
    from faster_whisper import WhisperModel
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe(model, audio_mono_float32, language="es"):
    segments, _info = model.transcribe(audio_mono_float32, language=language or None)
    return " ".join(seg.text.strip() for seg in segments).strip()


def synthesize(voice_model_path, text, out_wav):
    result = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(voice_model_path), "--output_file", str(out_wav)],
        input=text, text=True, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"piper synthesis failed: {result.stderr.strip()}")


def play_wav(wav_path):
    import numpy as np
    import soundcard as sc

    with wave.open(str(wav_path), "rb") as wf:
        samplerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    speaker = sc.default_speaker()
    speaker.play(audio, samplerate=samplerate)


def ask_claude(text, timeout=120):
    try:
        result = subprocess.run(
            ["claude", "-p", text],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "'claude' is not on PATH. Install the Claude Code CLI first "
            "(npm install -g @anthropic-ai/claude-code, then run `claude` "
            "once to log in) before the bridge can reach it."
        )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed: {result.stderr.strip()}")
    return result.stdout.strip()
