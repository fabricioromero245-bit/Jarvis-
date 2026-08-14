#!/usr/bin/env bash
# Step 1 of the voice-layer setup: read-only diagnostic.
# Installs nothing. Reports what's already on this machine and what
# it can run, so the STT/TTS install steps pick the right models.
set -uo pipefail

hr() { printf -- '-%.0s' $(seq 1 60); echo; }
have() { command -v "$1" >/dev/null 2>&1; }
ok()   { printf "  [x] %s\n" "$1"; }
miss() { printf "  [ ] %s\n" "$1"; }

echo "=== OS ==="
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "  $OS / $ARCH"
hr

echo "=== CPU / RAM ==="
if [ "$OS" = "Darwin" ]; then
  echo "  CPU cores: $(sysctl -n hw.ncpu 2>/dev/null || echo unknown)"
  MEM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  echo "  RAM: $(( MEM_BYTES / 1024 / 1024 / 1024 )) GB"
else
  echo "  CPU cores: $(nproc 2>/dev/null || echo unknown)"
  if have free; then
    free -h | awk '/^Mem:/ {print "  RAM: " $2 " total, " $7 " available"}'
  fi
fi
hr

echo "=== GPU ==="
if have nvidia-smi; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | sed 's/^/  NVIDIA: /'
elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
  echo "  Apple Silicon detected: Metal/MPS available for accelerated inference"
else
  echo "  No GPU detected — STT/TTS will run on CPU"
fi
hr

echo "=== Build tools ==="
have python3 && ok "python3 ($(python3 --version 2>&1))" || miss "python3"
have pip3    && ok "pip3" || miss "pip3 (needed to install faster-whisper / piper-tts / pynput / sounddevice)"
have git     && ok "git ($(git --version 2>&1))" || miss "git"
if have cc; then ok "cc ($(cc --version 2>&1 | head -1))"; elif have gcc; then ok "gcc ($(gcc --version 2>&1 | head -1))"; else miss "a C compiler (needed only if you choose whisper.cpp instead of faster-whisper)"; fi
have make    && ok "make" || miss "make (needed only for whisper.cpp)"
have ffmpeg  && ok "ffmpeg ($(ffmpeg -version 2>&1 | head -1))" || miss "ffmpeg"
hr

echo "=== Audio I/O library (PortAudio, backs sounddevice) ==="
if [ "$OS" = "Darwin" ]; then
  if have brew && brew list portaudio >/dev/null 2>&1; then ok "portaudio (brew)"; else miss "portaudio — install with: brew install portaudio"; fi
else
  if ldconfig -p 2>/dev/null | grep -qi libportaudio; then ok "libportaudio"; else miss "libportaudio — install with: sudo apt install portaudio19-dev (Debian/Ubuntu) or your distro's equivalent"; fi
fi
hr

echo "=== Existing STT engines ==="
if python3 -c "import faster_whisper" >/dev/null 2>&1; then ok "faster-whisper (pip)"; else miss "faster-whisper"; fi
if [ -d "$HOME/whisper.cpp" ] || have whisper-cli || have main; then ok "whisper.cpp"; else miss "whisper.cpp"; fi
hr

echo "=== Existing TTS engines ==="
if python3 -c "import piper" >/dev/null 2>&1 || have piper; then ok "piper"; else miss "piper"; fi
if python3 -c "import kokoro" >/dev/null 2>&1; then ok "kokoro"; else miss "kokoro"; fi
have espeak-ng && ok "espeak-ng (phonemizer dependency)" || miss "espeak-ng (needed by Piper/Kokoro for phonemization)"
hr

echo "=== Hotkey / audio Python deps ==="
python3 -c "import pynput" >/dev/null 2>&1 && ok "pynput" || miss "pynput"
python3 -c "import sounddevice" >/dev/null 2>&1 && ok "sounddevice" || miss "sounddevice"
hr

echo "=== Audio devices ==="
if [ "$OS" = "Darwin" ]; then
  system_profiler SPAudioDataType 2>/dev/null | grep -E "Input|Output|:" | head -20
else
  echo "  Input devices (arecord -l):"
  arecord -l 2>/dev/null | sed 's/^/    /' || echo "    arecord not found"
  echo "  Sources/sinks (pactl):"
  pactl list short sources 2>/dev/null | sed 's/^/    /' || echo "    pactl not found"
fi
hr

echo "=== claude CLI ==="
have claude && ok "claude ($(claude --version 2>&1))" || miss "claude CLI not on PATH — the bridge script calls it directly"
hr

echo "Done. Paste this whole output back and I'll pick model sizes + confirm the STT/TTS install plan before touching anything."
