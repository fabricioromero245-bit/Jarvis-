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
- [x] **4. `ptt.py`** — the push-to-talk daemon: hold a key, speak,
      release, and it runs mic → STT → `claude -p` → TTS → speakers,
      keeping `voice/state.json` live for the HUD. (Merged the planned
      `bridge.py` into this one file — no benefit to splitting them at
      this size.) **Confirmed 2026-08-14** working end to end after
      three real fixes found by testing on this machine: the `.cmd`
      shim needing `shell=True` on Windows, forcing UTF-8 decoding of
      Claude's response, and pinning the reply language explicitly.
- [x] **5. `start.py`** — one command: installs anything still missing
      (quietly, no prompts — steps 2-4 already got explicit
      confirmation), fetches the default voice if needed, and launches
      `ptt.py` with the configuration confirmed working on this
      machine. Extra args pass through, e.g. `python start.py --key f8`.

**Prerequisite for step 4**: `check_env.py` (step 1) showed `claude` is
not on this machine's PATH. `ptt.py` will record/transcribe/speak fine
without it, but the actual bridge to Claude will fail until it's
installed. Install it before testing step 4 end-to-end:
```powershell
npm install -g @anthropic-ai/claude-code
claude
```
(the second command runs it once to log in — needs Node.js; if `npm`
isn't found, install Node.js from https://nodejs.org first).

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

## Run step 4

Windows (PowerShell):
```powershell
cd voice
python ptt.py
```

macOS / Linux:
```bash
cd voice
python3 ptt.py
```

Asks `Proceed? [y/N]` (installs `pynput`, the only new dependency).
Then loads the STT model and waits. **Hold Caps Lock, speak, release
it** — it transcribes, prints `You: ...`, sends that to `claude -p`,
prints `Claude: ...`, then speaks the response through Piper. `Ctrl+C`
to quit.

While it's running, `voice/state.json` reflects what's actually
happening (`idle` / `listening` / `processing` / `speaking`, plus the
last transcript) — open the HUD (`hud/run.sh`) or the orb (`gui/`)
alongside it and both track it live.

**2026-08-14**: went through two other defaults first. F9 collided
with Edge's own "Reading mode" shortcut — pressing it while the orb
window (`gui/`) had focus popped up Edge's reader view instead of any
clear sign the hotkey worked. Then tried right Ctrl (the usual
push-to-talk convention), but this machine's keyboard only has one
Ctrl, on the left — the key doesn't physically exist here. Settled on
Caps Lock: present on every keyboard, unused for typing, and confirmed
via `debug_keys.py` to fire clean press/release events on this machine.

Options:
- `--key f8` (or any pynput key name — run `debug_keys.py` first to
  confirm your keyboard actually reports it the way you expect) if
  Caps Lock collides with something on your setup.
- `--language ''` for auto-detect instead of forced Spanish.
- `--skip-install` once `pynput` is already installed.

**Known limitation**: every `claude -p` call is a fresh, memoryless
conversation — nothing carries over turn to turn. `ptt.py` pins the
reply language explicitly per call (based on `--language`) so a short,
ambiguous turn doesn't come back in the wrong language, but it does
*not* give Claude any memory of the previous turn. If that turns out to
matter in practice, the fix is session continuity (`claude --continue`
or `--resume <id>`) — not built yet, flag it if you want it.

**2026-08-14, latency**: timing data (`[TIMING]` lines) showed
multi-paragraph replies costing 14-15s just to generate, then 27-36s to
speak — Claude was answering voice questions like a chat window
(headers, lists, long explanations). Every prompt now gets prefixed
with an instruction that this is a spoken conversation and to answer in
1-2 short sentences, no markdown/lists/code blocks — cuts both the
Claude generation time and the TTS playback time, since there's simply
less text to produce and speak.

Heads-up: holding a global keyboard hook is exactly the mechanism a
keylogger would use — some antivirus may flag `ptt.py` on first run.
That's expected for any push-to-talk tool and fine for a script you
wrote and control; you may need to allow it once.

## Run step 5 — the one command

Windows (PowerShell):
```powershell
cd voice
python start.py
```

macOS / Linux:
```bash
cd voice
python3 start.py
```

That's it — this is the command to remember day to day; steps 1-4 above
were the one-time setup. It installs anything still missing, fetches
the voice model if it isn't cached yet, and hands off to `ptt.py` with
Caps Lock / Spanish / `es_ES-davefx-medium` already configured.
Anything after `start.py` on the command line passes straight through
to `ptt.py`, so
`python start.py --key f8` still works.

## Voice quality: it sounds robotic

Piper is fast and light, not natural-sounding — that's the tradeoff we
made in step 3.

**2026-08-14**: tried pushing `--noise-scale`/`--noise-w`/`--length-scale`
above Piper's own defaults to add expressiveness — made it sound worse
(artifacts, not naturalness), not better. Reverted to Piper's stock
defaults (`length_scale=1.0`, `noise_scale=0.667`, `noise_w=0.8`) as the
actual best this voice model gets — the flags are still exposed on
`ptt.py`/`install_tts.py` if you want to experiment, but don't expect
tuning to fix this; Piper's ceiling is architectural.

The real fix is swapping the TTS engine for **Kokoro** (StyleTTS2-based,
~350MB voice) — genuinely more human-sounding, at the cost of a bigger
download and slower per-reply synthesis on this no-GPU machine.

**Caveat before committing to that swap**: Kokoro's standout quality is
specifically in English — that's the language it was primarily trained
on. Spanish support exists (via a community phonemizer, `misaki`,
falling back to `espeak-ng` for non-English/Japanese/Chinese languages)
but is less mature, and could plausibly sound *more* accented/synthetic
in Spanish than Piper's dedicated Spanish voice does, not less. There's
no local, offline, Spanish-native option better-established than Piper
right now within "runs locally" — this isn't a sure win. Worth trying
empirically since Piper's ceiling is confirmed too low, but going in
with that expectation set.
