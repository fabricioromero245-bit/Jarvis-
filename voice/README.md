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

Built in five steps, run in order, confirming before each install:

- [x] **1. `check_env.sh`** — read-only. Reports what's installed and what
      your machine can run. Installs nothing. **Run this and paste the
      output back before continuing.**
- [ ] **2. `install_stt.sh`** — installs the speech-to-text engine
      (faster-whisper or whisper.cpp) and downloads a model, sized to
      what step 1 found.
- [ ] **3. `install_tts.sh`** — installs the text-to-speech engine (Piper
      or Kokoro) and downloads a voice.
- [ ] **4. `ptt.py` + `bridge.py`** — the push-to-talk hotkey daemon and
      the loop that wires STT → `claude -p` → TTS together.
- [ ] **5. `start.sh`** — one command that brings the whole loop up.

## Run step 1

```bash
cd voice
./check_env.sh
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
