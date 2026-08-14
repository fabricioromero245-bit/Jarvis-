#!/usr/bin/env python3
"""Jarvis orb — cinematic desktop overlay for the voice layer.

Serves jarvis_orb.html and a /state endpoint (reading voice/state.json
live) over a local HTTP server, then opens it in Edge's borderless
"app mode" window. Pure standard library — no pip dependencies, no
native binaries — deliberately, after this session's repeated ARM64
Windows binary-compatibility surprises (PortAudio via sounddevice).
A local HTTP server + the browser already installed on the machine
sidesteps that whole class of risk.

If voice/state.json doesn't exist yet (ptt.py not running), /state
reports offline and the sphere just idles — same "honest degradation"
the HUD uses for the same reason.
"""

import json
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

GUI_DIR = Path(__file__).resolve().parent
REPO_ROOT = GUI_DIR.parent
STATE_PATH = REPO_ROOT / "voice" / "state.json"
HTML_PATH = GUI_DIR / "jarvis_orb.html"
HOST = "127.0.0.1"
PORT = 8765


def read_state():
    if not STATE_PATH.exists():
        return {"mic": "offline", "speaker": "offline"}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"mic": "offline", "speaker": "offline"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet — this runs alongside ptt.py's own output

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/state":
            body = json.dumps(read_state()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def find_edge():
    candidates = [
        shutil.which("msedge"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for exe in candidates:
        if exe and Path(exe).exists():
            return exe
    return None


def open_window(url):
    edge = find_edge()
    if edge:
        subprocess.Popen([edge, f"--app={url}", "--window-size=560,780"])
        return
    print("Could not find Edge for a borderless app window — opening a regular browser tab instead.")
    webbrowser.open(url)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Serving {url} (Ctrl+C to stop)")
    threading.Thread(target=open_window, args=(url,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
