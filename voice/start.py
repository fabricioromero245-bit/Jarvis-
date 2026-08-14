#!/usr/bin/env python3
"""Step 5: one command to start the voice layer.

Ensures dependencies + the default voice model are present (installing
quietly, no prompts — steps 2-4 already got explicit confirmation for
these installs), then launches ptt.py with the configuration confirmed
working on this machine: F9 push-to-talk, faster-whisper 'base' forced
to Spanish, Piper's es_ES-davefx-medium voice at its stock parameters.

Extra arguments pass straight through to ptt.py, e.g.:
    python start.py --key f8
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

VOICE_DIR = Path(__file__).resolve().parent
REQUIRED_PACKAGES = ["faster_whisper", "soundcard", "numpy", "piper", "pynput"]
DEFAULT_VOICE = "es_ES-davefx-medium"


def missing_packages():
    return [pkg for pkg in REQUIRED_PACKAGES if importlib.util.find_spec(pkg) is None]


def main():
    missing = missing_packages()
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])

    sys.path.insert(0, str(VOICE_DIR))
    from install_tts import ensure_voice

    voice_path = VOICE_DIR / "models" / f"{DEFAULT_VOICE}.onnx"
    if not voice_path.exists():
        print(f"Fetching voice '{DEFAULT_VOICE}'...")
        ensure_voice(DEFAULT_VOICE)

    subprocess.run([sys.executable, str(VOICE_DIR / "ptt.py"), "--skip-install", *sys.argv[1:]])


if __name__ == "__main__":
    main()
