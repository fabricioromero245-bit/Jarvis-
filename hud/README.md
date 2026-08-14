# Jarvis HUD

One-screen terminal instrument panel. No tabs, no fake charts — every
number and line is read straight off disk on every refresh.

```
┌───────────────────────────────────────────┐
│ JARVIS HUD                 date  time  up  │
├───────────────────┬─────────────────────────┤
│ VITALS            │ AUDIO I/O                │
├───────────────────┴─────────────────────────┤
│ COMMAND DECK (full width, all skills)        │
├───────────────────┬─────────────────────────┤
│ SCHEDULE — today  │ VAULT PULSE              │
└───────────────────┴─────────────────────────┘
```

## Run it

```bash
./hud/run.sh
```

That's the one command — it creates a `.venv` on first run, installs
`rich` + `pyyaml`, and launches. Every run after that just launches.
`Ctrl+C` to quit.

`./hud/run.sh --interval 5` slows the refresh (default 2s).
`./hud/run.sh --once` renders a single frame and exits — useful for
checking output without leaving it open, or piping to a screenshot tool.

## Where each panel's data comes from

Nothing here is typed in by hand at render time — the HUD only reads:

- **Vitals** — computed from the vault itself: total page count, daily
  new-capture / new-output counts, and `log.md` activity, all derived
  from frontmatter `created` dates and the log's own dated entries — no
  extra bookkeeping required. To track your own numbers (steps, focus
  hours, whatever), drop a file at `vault/raw/vitals/<slug>.md` with
  frontmatter `title: <label>` and body lines:
  ```
  - 2026-08-14T09:00 62
  - 2026-08-14T14:00 71
  ```
  Append to it (script, cron job, or by hand) and it shows up with a
  sparkline on the next refresh. Documented in `vault/CLAUDE.md`.

- **Command deck** — scans `~/.claude/skills/**/SKILL.md` directly, the
  real Claude Code skill registry. `●` = org-synced skill, `○` =
  personal. This means it's never stale relative to what's actually
  installed, and never needs updating by hand.

- **Schedule** — `vault/raw/schedule/YYYY-MM-DD.md`, one line per block:
  `- HH:MM label`. The HUD highlights whichever block's start time has
  most recently passed. A placeholder file for today is already seeded —
  edit it, or point a calendar-sync script at writing it each morning
  (the `morning` skill is a natural fit for that later).

- **Audio I/O** — reads `voice/state.json`. This doesn't exist until the
  push-to-talk daemon (step 4 of the voice layer, not built yet) starts
  writing to it, so right now this panel honestly shows "offline" rather
  than faking a listening state. Once the daemon runs, it just needs to
  write:
  ```json
  {"mic": "listening", "speaker": "idle", "last_transcript": "...", "updated": "<ISO timestamp>"}
  ```
  on every state change. If `updated` is more than 15s stale, the HUD
  shows offline rather than trust a dead process's last write.

- **Vault pulse** — the last 5 lines of `vault/log.md`. The one panel
  that's literally nothing but "what changed in the vault most recently."

## Changing it by voice, later

Two different things can change here, and they behave differently:

- **Vault data** (schedule, vitals, skills, log) — no voice command
  needed at all, and no restart. Say "add a 2pm dentist appointment" to
  the (future) push-to-talk bridge, it appends a line to today's
  schedule file, and the HUD picks it up on its next 2-second refresh
  automatically, because it re-reads the vault every cycle.

- **The HUD itself** (layout, colors, what counts as a vital, panel
  order) — say something like "make the vitals panel show weekly
  numbers instead of daily" to the voice bridge. That transcript goes to
  `claude -p "<instruction>"` against this repo the same way any other
  voice command would, and Claude edits `hud/hud.py` / `vault_reader.py`
  directly. Unlike vault-data changes, **this needs a restart** — Python
  doesn't hot-reload its own source, so after the edit lands, `Ctrl+C`
  and run `./hud/run.sh` again to pick it up.
