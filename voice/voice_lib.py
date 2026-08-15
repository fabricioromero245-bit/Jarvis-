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


_tts_cache = {}  # voice_model_path (str) -> loaded PiperVoice, or None if in-process loading failed


def _get_piper_voice(voice_model_path):
    key = str(voice_model_path)
    if key in _tts_cache:
        return _tts_cache[key]
    try:
        from piper import PiperVoice
        voice = PiperVoice.load(key)
    except Exception as e:
        print(f"[TTS] in-process Piper unavailable ({e}); using a fresh subprocess per reply instead")
        voice = None
    _tts_cache[key] = voice
    return voice


def synthesize(voice_model_path, text, out_wav, length_scale=1.0, noise_scale=0.667, noise_w=0.8):
    # Reverted to Piper's own defaults 2026-08-14: pushing noise_scale/
    # noise_w higher to sound more "expressive" instead made it sound
    # worse (artifacts, not naturalness) — the model already sounds best
    # near its trained defaults. Piper's ceiling is architectural, not a
    # tuning problem — see voice/README.md.
    #
    # Timing showed every reply paying ~7.5s here, not just the first —
    # each call was spawning a brand-new `python -m piper` process that
    # reloads the ~60MB voice model from scratch every time, unlike the
    # STT model which loads once and stays warm. Load the voice once
    # in-process and reuse it; fall back to the proven subprocess path
    # (same model, same params, just slower) if that fails for any reason.
    voice = _get_piper_voice(voice_model_path)
    if voice is not None:
        try:
            from piper import SynthesisConfig
            syn_config = SynthesisConfig(length_scale=length_scale, noise_scale=noise_scale, noise_w_scale=noise_w)
            with wave.open(str(out_wav), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file, syn_config=syn_config)
            return
        except Exception as e:
            print(f"[TTS] in-process synthesis failed ({e}); falling back to subprocess for this reply")

    result = subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(voice_model_path), "--output_file", str(out_wav),
         "--length_scale", str(length_scale), "--noise_scale", str(noise_scale), "--noise_w", str(noise_w)],
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


def ask_claude(text, timeout=120, extra_dirs=None, web_search=True):
    # On Windows, the npm-installed `claude` command is a .cmd shim, not a
    # native .exe. cmd.exe/PowerShell resolve that automatically; Python's
    # subprocess (CreateProcess) does not, unless run through a shell —
    # hence shell=True on Windows only. The input here is the user's own
    # speech, transcribed locally on their own machine, not external/
    # adversarial input, so the usual shell-injection concern doesn't apply.
    #
    # extra_dirs grants Claude Code read/write access to project folders
    # beyond its own cwd (e.g. the vault, other repos) via --add-dir —
    # this is how Jarvis gets to "know about" more than one project.
    add_dir_flags = []
    for d in (extra_dirs or []):
        add_dir_flags += ["--add-dir", str(d)]

    # `-p` (non-interactive) mode has no way to show an approval prompt,
    # so tool use is denied by default — confirmed in a sandbox that a
    # plain `claude -p "search the web..."` refuses with a permission
    # error. --allowedTools WebSearch pre-approves just that one tool
    # (not a blanket bypass of all permission checks) and was confirmed
    # to actually perform real searches with cited sources, not a no-op.
    tool_flags = ["--allowedTools", "WebSearch"] if web_search else []

    try:
        result = subprocess.run(
            ["claude", *add_dir_flags, *tool_flags, "-p", text],
            capture_output=True, text=True, timeout=timeout,
            shell=(sys.platform == "win32"),
            encoding="utf-8", errors="replace",
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
