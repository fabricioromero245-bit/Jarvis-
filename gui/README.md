# Jarvis orb

The cinematic desktop overlay: a rotating sphere of ~190 neurons
connected by synapses, breathing and firing in reaction to what the
voice layer (`voice/ptt.py`) is doing right now. Same underlying data
as the terminal HUD's Audio I/O panel (`voice/state.json`) — this is
just a very different presentation of it.

## Run it

```bash
python server.py
```

(Windows: `python server.py`; macOS/Linux: `python3 server.py`.) No
install step — everything here is Python standard library, zero pip
dependencies.

That starts a local HTTP server on `127.0.0.1:8765` and opens the page
in Edge's borderless "app mode" window (no tabs, no address bar — just
the instrument). `Ctrl+C` in the terminal stops it.

If `voice/ptt.py` isn't running yet, the sphere just idles calmly —
`/state` reports `offline` and the page treats that the same as `idle`,
matching the HUD's "honest degradation" instead of faking activity.

## Why a local server instead of a proper desktop window library

The obvious choice here is something like `pywebview` — a real desktop
window wrapping a webview. It was deliberately not used: this session
already hit two rounds of a pip package bundling a native binary that
turned out to be broken specifically on this machine's Windows ARM64
build (`sounddevice`'s PortAudio DLL, twice — see `voice/README.md`).
`pywebview`'s Windows backend depends on `pythonnet` (a .NET/CLR
bridge) to talk to the WebView2 runtime, and `pythonnet`'s ARM64
Windows wheel support has historically been patchier than mainstream
x64 — a real risk of hitting the same class of problem a third time.

Instead: a stdlib-only HTTP server (`http.server`) serves the page and
a `/state` endpoint, and the already-installed, definitely-ARM64-native
Edge browser displays it via `--app=` (Chrome/Edge's site-specific-app
mode — borderless, no browser chrome). Zero new native binaries, zero
pip installs, using only things already proven to work on this exact
machine.

If Edge isn't found at its usual install paths, it falls back to
opening a regular browser tab (functional, just not borderless).

## Files

- `jarvis_orb.html` — the page: canvas-rendered neuron sphere, polls
  `/state` every 300ms via `fetch`, maps `{mic, speaker}` to one of
  four visual states (idle / listening / processing / speaking).
- `server.py` — the HTTP server + Edge-launcher. This is the one
  command.

## Design notes (for future edits)

- **Color is fixed** (turquoise, `rgb(45 212 191)`) across every state
  by design — the user explicitly did not want state to be color-coded
  here, unlike the terminal HUD. Don't reintroduce per-state color
  without asking; this was a deliberate revert.
- **State drives**: rotation speed, fire rate (how often neurons spark),
  cascade probability (how far a spark propagates through synapses),
  pulse travel speed, and a "breathing" contraction/expansion of the
  whole sphere — strongest during `listening`, since that's when the
  user is actively speaking to it.
- `mapToVisualState` collapses `voice/state.json`'s two independent
  fields (`mic`, `speaker`) into one of four visual states — `speaking`
  wins if the speaker is active, otherwise `mic` decides. Extending
  states later means updating both `STATES` in `jarvis_orb.html` and
  this mapping function together.
