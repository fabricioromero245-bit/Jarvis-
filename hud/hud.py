#!/usr/bin/env python3
"""Jarvis HUD — one-screen instrument panel, read straight off the vault.

No cached state: every refresh re-reads the vault, the skill registry,
and the voice-layer state file from disk.
"""

import argparse
import datetime
import time
from pathlib import Path

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import vault_reader as vr

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = REPO_ROOT / "vault"

MUTED = "grey58"
DIM_BORDER = "grey37"
GOOD = "green3"
WARN = "yellow3"
BAD = "red3"
ACCENT = "cyan"

BLOCKS = " ▁▂▃▄▅▆▇█"


def sparkline(values):
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return BLOCKS[4 if hi else 1] * len(values)
    span = hi - lo
    return "".join(BLOCKS[1 + int((v - lo) / span * 7)] for v in values)


def panel(title, renderable, size=None):
    return Panel(
        renderable,
        title=f"[bold {ACCENT}]{title}[/]",
        title_align="left",
        border_style=DIM_BORDER,
        padding=(0, 1),
    )


def build_header():
    now = datetime.datetime.now()
    uptime = now - build_header.started
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    left = Text("JARVIS HUD", style=f"bold {ACCENT}")
    right = Text(f"{now:%Y-%m-%d  %H:%M:%S}   up {h:02d}:{m:02d}:{s:02d}", style=MUTED)
    row = Table.grid(expand=True)
    row.add_column(justify="left")
    row.add_column(justify="right")
    row.add_row(left, right)
    return Panel(row, border_style=DIM_BORDER, padding=(0, 1))


build_header.started = datetime.datetime.now()


def build_vitals():
    table = Table.grid(padding=(0, 1), expand=True)
    table.add_column(style=MUTED, no_wrap=True)
    table.add_column(justify="right", style="bold white", no_wrap=True)
    table.add_column(style=ACCENT, no_wrap=True)

    wiki_total, wiki_trend = vr.folder_trend(VAULT_ROOT / "wiki")
    raw_total, raw_trend = vr.folder_trend(VAULT_ROOT / "raw")
    out_total, out_trend = vr.folder_trend(VAULT_ROOT / "outputs")
    activity_trend = vr.log_activity_trend(VAULT_ROOT)

    rows = [
        ("vault pages", wiki_total + raw_total + out_total,
         [w + r + o for w, r, o in zip(wiki_trend, raw_trend, out_trend)]),
        ("captures/day", raw_trend[-1], raw_trend),
        ("outputs/day", out_trend[-1], out_trend),
        ("log activity/day", activity_trend[-1], activity_trend),
    ]
    custom = vr.read_custom_vitals(VAULT_ROOT)
    for label, current, trend in rows:
        table.add_row(label, str(current), sparkline(trend))
    for label, values in custom:
        table.add_row(label, f"{values[-1]:g}", sparkline(values))

    return panel("VITALS", table), len(rows) + len(custom) + 3


def build_deck(width):
    skills = vr.discover_skills()
    if not skills:
        return panel("COMMAND DECK", Text("no skills found under ~/.claude/skills", style=MUTED)), 4

    pairs_per_row = max(2, min(6, width // 26))
    table = Table.grid(padding=(0, 2), expand=True)
    for _ in range(pairs_per_row):
        table.add_column(no_wrap=True)

    rows = [skills[i:i + pairs_per_row] for i in range(0, len(skills), pairs_per_row)]
    for row_skills in rows:
        cells = []
        for s in row_skills:
            dot_style = ACCENT if s["status"] == "synced" else GOOD
            dot = "●" if s["status"] == "synced" else "○"
            cells.append(Text.assemble((f"{dot} ", dot_style), (s["name"], "white")))
        cells += [Text("")] * (pairs_per_row - len(cells))
        table.add_row(*cells)

    legend = Text.assemble(("● ", ACCENT), ("synced   ", MUTED), ("○ ", GOOD), ("personal", MUTED))
    body = Group(table, Text(""), legend)
    return panel(f"COMMAND DECK ({len(skills)})", body), len(rows) + 4


def build_audio():
    state = vr.read_audio_state(REPO_ROOT)
    mic, speaker = state.get("mic", "offline"), state.get("speaker", "offline")

    def color(v):
        return GOOD if v not in ("offline", "idle") else MUTED

    def dot(v):
        return "●" if v not in ("offline",) else "○"

    lines = [
        Text.assemble(("mic       ", MUTED), (f"{dot(mic)} {mic}", color(mic))),
        Text.assemble(("speaker   ", MUTED), (f"{dot(speaker)} {speaker}", color(speaker))),
    ]
    note = state.get("note")
    if note:
        lines.append(Text(note, style=WARN if mic == "offline" else MUTED))
    transcript = state.get("last_transcript")
    if transcript:
        lines.append(Text(f'"{transcript}"', style=MUTED, no_wrap=True, overflow="ellipsis"))
    return panel("AUDIO I/O", Group(*lines)), len(lines) + 3


def build_schedule():
    blocks, current_idx = vr.read_schedule(VAULT_ROOT)
    if blocks is None:
        body = Text("no schedule file for today\n"
                     f"create vault/raw/schedule/{datetime.date.today()}.md", style=MUTED)
        return panel("SCHEDULE", body), 5
    if not blocks:
        return panel("SCHEDULE — today", Text("(empty — no blocks parsed)", style=MUTED)), 4

    table = Table.grid(padding=(0, 1), expand=True)
    table.add_column(style=MUTED, no_wrap=True)
    table.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column(no_wrap=True)
    for i, (t, label) in enumerate(blocks):
        is_now = i == current_idx
        t_style = f"bold {ACCENT}" if is_now else MUTED
        label_style = "bold white" if is_now else "white"
        marker = Text("◀ now", style=f"bold {GOOD}") if is_now else Text("")
        table.add_row(Text(t, style=t_style), Text(label, style=label_style), marker)
    return panel("SCHEDULE — today", table), len(blocks) + 3


def build_pulse():
    entries = vr.tail_log(VAULT_ROOT, n=5)
    if not entries:
        return panel("VAULT PULSE", Text("log.md is empty", style=MUTED)), 4
    lines = [Text(e, style=MUTED, overflow="ellipsis", no_wrap=True) for e in entries]
    return panel("VAULT PULSE", Group(*lines)), len(lines) + 3


def build_layout(width):
    vitals_panel, vitals_size = build_vitals()
    audio_panel, audio_size = build_audio()
    deck_panel, deck_size = build_deck(width)
    schedule_panel, schedule_size = build_schedule()
    pulse_panel, pulse_size = build_pulse()

    top_size = max(vitals_size, audio_size, 6)
    bottom_size = max(schedule_size, pulse_size, 5)
    deck_size = max(deck_size, 5)

    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="top", size=top_size),
        Layout(name="deck", size=deck_size),
        Layout(name="bottom", size=bottom_size),
    )
    layout["top"].split_row(Layout(name="vitals"), Layout(name="audio"))
    layout["bottom"].split_row(Layout(name="schedule"), Layout(name="pulse"))

    layout["header"].update(build_header())
    layout["vitals"].update(vitals_panel)
    layout["audio"].update(audio_panel)
    layout["deck"].update(deck_panel)
    layout["schedule"].update(schedule_panel)
    layout["pulse"].update(pulse_panel)
    return layout


def main():
    ap = argparse.ArgumentParser(description="Jarvis terminal HUD")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between refreshes")
    ap.add_argument("--once", action="store_true", help="render a single frame and exit (for testing)")
    args = ap.parse_args()

    console = Console()
    if args.once:
        console.print(build_layout(console.size.width))
        return

    try:
        with Live(build_layout(console.size.width), console=console, screen=True, refresh_per_second=4) as live:
            while True:
                time.sleep(args.interval)
                live.update(build_layout(console.size.width))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
