#!/usr/bin/env python3
"""Step 1 of the voice-layer setup: read-only diagnostic.

Installs nothing. Reports what's already on this machine and what it
can run, so the STT/TTS install steps (step 2/3) pick the right engine
and model size. Pure standard library — runs before any dependency
exists, on Windows, macOS, or Linux.
"""

import ctypes
import platform
import shutil
import subprocess
import sys

OS = platform.system()  # 'Windows', 'Darwin', 'Linux'


def hr():
    print("-" * 60)


def have(cmd):
    return shutil.which(cmd) is not None


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return out.stdout.strip()
    except Exception:
        return ""


def status(found, label, hint=None):
    mark = "[x]" if found else "[ ]"
    line = f"  {mark} {label}"
    if not found and hint:
        line += f" — {hint}"
    print(line)


def section(title):
    print(f"\n=== {title} ===")


def check_os():
    section("OS")
    print(f"  {OS} / {platform.machine()}  (Python {platform.python_version()})")
    hr()


def check_cpu_ram():
    section("CPU / RAM")
    print(f"  CPU cores: {__import__('os').cpu_count()}")
    if OS == "Windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total_gb = stat.ullTotalPhys / (1024 ** 3)
        avail_gb = stat.ullAvailPhys / (1024 ** 3)
        print(f"  RAM: {total_gb:.1f} GB total, {avail_gb:.1f} GB available")
    elif OS == "Darwin":
        total = run(["sysctl", "-n", "hw.memsize"])
        if total:
            print(f"  RAM: {int(total) / (1024 ** 3):.1f} GB total")
    else:
        try:
            with open("/proc/meminfo") as f:
                meminfo = dict(
                    (line.split(":")[0], line.split(":")[1].strip())
                    for line in f if ":" in line
                )
            total_kb = int(meminfo["MemTotal"].split()[0])
            avail_kb = int(meminfo.get("MemAvailable", "0 kB").split()[0])
            print(f"  RAM: {total_kb / 1024 / 1024:.1f} GB total, {avail_kb / 1024 / 1024:.1f} GB available")
        except Exception:
            print("  RAM: could not read /proc/meminfo")
    hr()


def check_gpu():
    section("GPU")
    if have("nvidia-smi"):
        out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
        print(f"  NVIDIA: {out}" if out else "  nvidia-smi found but returned nothing")
    elif OS == "Darwin" and platform.machine() == "arm64":
        print("  Apple Silicon detected: Metal/MPS available for accelerated inference")
    else:
        print("  No GPU detected — STT/TTS will run on CPU")
    hr()


def check_build_tools():
    section("Build tools")
    status(have("python3") or have("python"), "python", )
    status(have("pip3") or have("pip"), "pip", "needed to install faster-whisper / piper-tts / pynput / sounddevice")
    status(have("git"), "git")
    has_cc = have("cc") or have("gcc") or have("cl") or have("clang")
    status(has_cc, "C compiler", "needed only if you choose whisper.cpp instead of faster-whisper")
    status(have("make") or have("nmake"), "make", "needed only for whisper.cpp")
    status(have("ffmpeg"), "ffmpeg")
    hr()


def check_portaudio():
    section("Audio I/O library (PortAudio, backs sounddevice)")
    if OS == "Windows":
        print("  sounddevice ships PortAudio bundled in its Windows wheel —")
        print("  nothing to install separately, it'll come in with `pip install sounddevice`.")
    elif OS == "Darwin":
        out = run(["brew", "list", "portaudio"])
        status(bool(out), "portaudio (brew)", "install with: brew install portaudio")
    else:
        out = run(["bash", "-c", "ldconfig -p 2>/dev/null | grep -i libportaudio"])
        status(bool(out), "libportaudio", "install with: sudo apt install portaudio19-dev (or your distro's equivalent)")
    hr()


def check_python_pkg(mod):
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def check_stt_tts():
    section("Existing STT engines")
    status(check_python_pkg("faster_whisper"), "faster-whisper (pip)")
    status(have("whisper-cli") or have("main"), "whisper.cpp")
    hr()

    section("Existing TTS engines")
    status(check_python_pkg("piper") or have("piper"), "piper")
    status(check_python_pkg("kokoro"), "kokoro")
    status(have("espeak-ng"), "espeak-ng (phonemizer dependency — optional, depends on TTS engine version)")
    hr()

    section("Hotkey / audio Python deps")
    status(check_python_pkg("pynput"), "pynput")
    status(check_python_pkg("sounddevice"), "sounddevice")
    hr()


def check_audio_devices():
    section("Audio devices")
    if check_python_pkg("sounddevice"):
        import sounddevice as sd
        for d in sd.query_devices():
            kind = "in" if d["max_input_channels"] > 0 else "out"
            print(f"  [{kind}] {d['name']}")
    else:
        print("  sounddevice not installed yet — device list will show once it's installed in step 4")
    hr()


def check_claude_cli():
    section("claude CLI")
    status(have("claude"), "claude", "not on PATH — the bridge script calls it directly")
    hr()


def main():
    check_os()
    check_cpu_ram()
    check_gpu()
    check_build_tools()
    check_portaudio()
    check_stt_tts()
    check_audio_devices()
    check_claude_cli()
    print("Done. Paste this whole output back and I'll pick model sizes + confirm")
    print("the STT/TTS install plan before touching anything.")


if __name__ == "__main__":
    main()
