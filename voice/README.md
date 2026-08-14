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

- [x] **1. `check_env.py`** — read-only. Reports what's installed and
      what your machine can run. Installs nothing. **Run this and paste
      the output back before continuing.**
- [x] **2. `install_stt.py`** — installs faster-whisper + the `base`
      model (CPU-only, no GPU / no C compiler on this machine ruled out
      whisper.cpp), records 5s of audio, and prints the transcript.
      **Run this and paste the transcript back before continuing.**
- [ ] **3. `install_tts.py`** — installs the text-to-speech engine (Piper
      or Kokoro) and downloads a voice.
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
