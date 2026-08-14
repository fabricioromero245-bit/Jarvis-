"""Read-only accessors for HUD panels. Every function re-reads from disk —
the HUD is only ever a window onto the vault, never a cache of it."""

import datetime
import json
import re
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
LOG_LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2})")
VITAL_LINE_RE = re.compile(r"^- \S+\s+(-?\d+(?:\.\d+)?)")
SCHEDULE_LINE_RE = re.compile(r"^- (\d{2}:\d{2})\s+(.+)$")
SKIP_NAMES = {"index.md", "log.md", "README.md", "CLAUDE.md"}


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return data, text[m.end():]


def _read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def iter_pages(folder):
    if not folder.exists():
        return
    for p in sorted(folder.rglob("*.md")):
        if p.name not in SKIP_NAMES:
            yield p


def _page_created_date(path):
    meta, _ = parse_frontmatter(_read(path))
    created = meta.get("created")
    if created:
        try:
            return datetime.date.fromisoformat(str(created))
        except ValueError:
            pass
    return datetime.date.fromtimestamp(path.stat().st_mtime)


def _daily_buckets(days):
    today = datetime.date.today()
    return {today - datetime.timedelta(days=i): 0 for i in range(days)}, today


def _ordered(buckets, today, days):
    return [buckets[today - datetime.timedelta(days=i)] for i in range(days - 1, -1, -1)]


def folder_trend(folder, days=14):
    """(total page count, list of daily new-page counts oldest->newest)."""
    buckets, today = _daily_buckets(days)
    total = 0
    for p in iter_pages(folder):
        total += 1
        d = _page_created_date(p)
        if d in buckets:
            buckets[d] += 1
    return total, _ordered(buckets, today, days)


def log_activity_trend(vault_root, days=14):
    log_path = vault_root / "log.md"
    buckets, today = _daily_buckets(days)
    if log_path.exists():
        for line in _read(log_path).splitlines():
            m = LOG_LINE_RE.match(line.strip())
            if m:
                d = datetime.date.fromisoformat(m.group(1))
                if d in buckets:
                    buckets[d] += 1
    return _ordered(buckets, today, days)


def tail_log(vault_root, n=5):
    log_path = vault_root / "log.md"
    if not log_path.exists():
        return []
    lines = [l.strip() for l in _read(log_path).splitlines() if l.strip().startswith("- ")]
    return lines[-n:]


def read_custom_vitals(vault_root, max_points=20):
    """Any file in raw/vitals/*.md is a hand- or script-fed metric:
    body lines of the form '- <timestamp> <number>'."""
    vitals_dir = vault_root / "raw" / "vitals"
    out = []
    if not vitals_dir.exists():
        return out
    for p in sorted(vitals_dir.glob("*.md")):
        meta, body = parse_frontmatter(_read(p))
        label = meta.get("title", p.stem)
        values = [float(m.group(1)) for m in
                  (VITAL_LINE_RE.match(l.strip()) for l in body.splitlines()) if m]
        if values:
            out.append((label, values[-max_points:]))
    return out


def discover_skills():
    """Scan the real Claude Code skill registry — not a vault file, this
    is the live source of truth for 'what skills exist'."""
    roots = [Path.home() / ".claude" / "skills", Path.cwd() / ".claude" / "skills"]
    skills, seen = [], set()
    for root in roots:
        if not root.exists():
            continue
        for skill_md in sorted(root.rglob("SKILL.md")):
            meta, _ = parse_frontmatter(_read(skill_md))
            name = meta.get("name", skill_md.parent.name)
            if name in seen:
                continue
            seen.add(name)
            status = "synced" if "synced" in skill_md.parts else "personal"
            skills.append({
                "name": name,
                "description": (meta.get("description") or "").strip(),
                "status": status,
            })
    return skills


def read_schedule(vault_root):
    """Today's blocks from raw/schedule/YYYY-MM-DD.md, plus which one is
    current. Returns (blocks, current_index) or (None, None) if no file."""
    path = vault_root / "raw" / "schedule" / f"{datetime.date.today().isoformat()}.md"
    if not path.exists():
        return None, None
    _, body = parse_frontmatter(_read(path))
    blocks = [(m.group(1), m.group(2)) for m in
              (SCHEDULE_LINE_RE.match(l.strip()) for l in body.splitlines()) if m]
    now = datetime.datetime.now().strftime("%H:%M")
    current_idx = None
    for i, (t, _) in enumerate(blocks):
        if t <= now:
            current_idx = i
    return blocks, current_idx


def read_audio_state(repo_root, stale_seconds=15):
    """Voice layer runtime state — not vault knowledge, so it lives
    outside the vault as a small JSON file the daemon writes to."""
    path = repo_root / "voice" / "state.json"
    offline = {"mic": "offline", "speaker": "offline", "note": "voice layer not running"}
    if not path.exists():
        return offline
    try:
        data = json.loads(_read(path))
    except (json.JSONDecodeError, OSError):
        return {"mic": "offline", "speaker": "offline", "note": "state file unreadable"}
    updated = data.get("updated")
    if updated:
        try:
            ts = datetime.datetime.fromisoformat(updated)
            if (datetime.datetime.now() - ts).total_seconds() > stale_seconds:
                return {"mic": "offline", "speaker": "offline", "note": "voice layer stale"}
        except ValueError:
            pass
    return data
