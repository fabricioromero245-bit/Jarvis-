# Voice layer

Push-to-talk voice interface to Claude Code. Everything runs locally —
speech-to-text and text-to-speech never send audio anywhere.

```
you hold hotkey → mic records → release → local STT → text
                                                          │
                                                          ▼
                                              claude -p "<text>"
                                                          │
                                                          ▼
                                          response text → local TTS → speakers
```

## Status

Built in five steps, run in order, confirming before each install.
Everything is Python (no `.sh` scripts) so the same steps work
unchanged on Windows, macOS, or Linux — no WSL, no bash required.

**Confirmed working on**: Windows on ARM64 (Snapdragon-class laptop),
Python 3.14, faster-whisper `base` model, CPU-only.

**Audio backend note**: both scripts use `soundcard`, not `sounddevice`.
`sounddevice` bundles a prebuilt native PortAudio binary per platform;
its ARM64 Windows build proved unreliable here — it raised `OSError:
cannot load library '...libportaudioarm64.dll' ... error 0x7e`, worked
exactly once after installing the matching Visual C++ Redistributable,
then failed again on every later run even with that redistributable
confirmed present (`winget list` showed it already installed and up to
date — so that was never actually the cause). `soundcard` sidesteps the
whole problem: on Windows it talks to WASAPI directly via ctypes/COM
instead of shipping a compiled binary blob, so there's no niche
ARM64-specific artifact that can be broken or mismatched.

- [x] **1. `check_env.py`** — read-only. Reports what's installed and
      what your machine can run. Installs nothing. **Run this and paste
      the output back before continuing.**
- [x] **2. `install_stt.py`** — installs faster-whisper + the `base`
      model (CPU-only, no GPU / no C compiler on this machine ruled out
      whisper.cpp), records 5s of audio, and prints the transcript.
      **Confirmed 2026-08-14** after forcing `--language es`:
      `Transcript: 'hola buenas noches hola buenas noches'` (es,
      confidence 1.00) against spoken "hola, buenas noches".
- [x] **3. `install_tts.py`** — installs Piper + a Spanish voice
      (`es_ES-davefx-medium`, ~60MB — Kokoro would be ~350MB and there's
      no GPU here to justify it), synthesizes a test sentence, and plays
      it back. **Confirmed 2026-08-14: heard "Hola, este es Jarvis
      probando la voz." out loud.**
- [ ] **4. `ptt.py` + `bridge.py`** — the push-to-talk hotkey daemon and
      the loop that wires STT → `claude -p` → TTS together.
- [ ] **5. `start.py`** — one command that brings the whole loop up.

## Run step 1

Windows (PowerShell):
```powershell
cd voice
python check_env.py
```

macOS / Linux:
```bash
cd voice
python3 check_env.py
```

Paste the full output back. It's used to decide:

- **STT engine + model size** — faster-whisper (default, pip-only) vs.
  whisper.cpp (if you'd rather not add the pip dependency); tiny/base
  for low RAM or CPU-only, small/medium if you've got a GPU or more RAM.
- **TTS engine** — Piper (default, lightweight, one binary + small voice
  model) vs. Kokoro (heavier, higher quality, needs more RAM).
- **Missing build tools** — portaudio, espeak-ng, a C compiler if you go
  the whisper.cpp route — called out explicitly so nothing fails silently
  mid-install.

Nothing gets installed until you've seen the plan based on your actual
machine and confirmed it.

## Run step 2

Windows (PowerShell):
```powershell
cd voice
python install_stt.py
```

macOS / Linux:
```bash
cd voice
python3 install_stt.py
```

It asks `Proceed? [y/N]` before installing anything. After installing,
it loads the model, then waits for Enter and records 5 seconds of audio,
transcribes it, and prints the text. Paste that output back — if the
transcript matches what you said, step 2 is done and step 3 (TTS) is next.

If it feels slow or the machine is tight on RAM, rerun with a smaller
model: `python install_stt.py --model tiny` (only re-downloads if you
haven't already fetched that size).

**2026-08-14**: verified once with `sounddevice` (`Transcript: 'Hola,
hola buenos días'`), then `sounddevice` started failing consistently on
later runs (see the audio backend note above). Switched to `soundcard`
— recording itself then worked, but language auto-detection guessed
English on a short Spanish clip and mangled the transcript. Now forces
Spanish by default (`--language es`); pass `--language ''` to go back to
auto-detect, or another ISO code for a different language.

## Run step 3

Windows (PowerShell):
```powershell
cd voice
python install_tts.py
```

macOS / Linux:
```bash
cd voice
python3 install_tts.py
```

Asks `Proceed? [y/N]` before installing. Downloads the voice into
`voice/models/` (gitignored — it's a binary model file, not something
that belongs in the repo), synthesizes the default sentence, and plays
it through your speakers. Paste the output back — if you heard it,
step 3 is done and step 4 (the push-to-talk hotkey + full loop) is next.

I could not pre-verify the voice download URL from here — this session
runs in a sandbox whose network policy blocks huggingface.co outright,
unrelated to whether the file exists. If `install_tts.py` fails on the
download step, paste the exact error and I'll fix the voice name/URL.

Options:
- `--voice en_US-lessac-medium` for an English voice instead (same
  Piper install, just a different model download).
- `--text "..."` to test with your own sentence.
- `--skip-install` to skip pip and just re-fetch the voice / re-speak,
  once piper-tts is already installed.
