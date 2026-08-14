# Vault schema — read this before writing anything

This vault is the memory layer for the AI operating system. It is a plain
markdown store: no database, no binary formats, no hidden state. Everything
in it must be readable by a human in a plain text editor.

Read this file at the start of any session that touches the vault, before
creating, editing, or moving a single file.

## Structure

- `raw/` — everything captured, unedited. Transcripts, clips, dumps, pasted
  material. Written once, not rewritten in place. If a raw capture gets
  distilled into understanding, that understanding goes in `wiki/` as a
  new or updated page — the raw file stays untouched as the source record.
- `wiki/` — distilled knowledge, one page per topic. This is what the
  system *knows*, as opposed to what it merely captured. Rewritten in
  place as understanding improves; a wiki page is never append-only.
- `outputs/` — everything a skill or task ships: reports, drafts, plans.
  Write-once, dated, never edited after the fact.

## Hard rules

1. **Markdown only.** No database, no binary formats. If it can't be read
   in a plain text editor, it doesn't belong in the vault.

2. **Every page carries YAML frontmatter** — raw, wiki, and output pages
   alike:

   ```yaml
   ---
   title: <human-readable title>
   type: raw | wiki | output
   tags: [tag1, tag2]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   summary: one sentence describing what this page is / says
   ---
   ```

   `created` is set once and never changes. `updated` moves every time the
   body changes. For `raw/` and `outputs/`, `created` and `updated` are
   the same, since those are write-once.

3. **Link pages with wikilinks**: `[[Page Title]]`, matching the target
   page's `title` frontmatter field (not its filename). The vault is a
   graph, not a folder tree — prefer linking to an existing wiki page over
   re-explaining its content. A wiki page that references a raw source
   should link to it; a raw page doesn't need to link forward.

4. **Skill/task output lands in `outputs/`, filename dated**:
   `outputs/YYYY-MM-DD-slug.md`. Never write skill output into `raw/` or
   `wiki/` directly. If an output should also update what the system
   knows, write the output *and* update the relevant `wiki/` page, with
   the wiki page linking back to the output as evidence.

5. **`index.md` lists every page in the vault**, one line each, grouped by
   folder, with a one-line hook (usually the page's `summary`). Update it
   in the same edit that adds or removes a page — it must never drift out
   of sync with the folder contents.

6. **`log.md` is append-only.** Add a dated entry for every meaningful
   change: new page, rewrite, merge, deletion. Newest entry at the bottom.
   Never edit or delete a past entry — if something was wrong, correct it
   forward with a new entry, don't rewrite history.

## Writing to this vault, in practice

- **Capturing something** (a transcript, a clip, a raw dump) →
  `raw/YYYY-MM-DD-slug.md`, `type: raw`. Write it and leave it.
- **Learning something** (new understanding, or a correction to existing
  understanding) → `wiki/<Topic>.md`, `type: wiki`. Rewrite the page
  rather than appending noise to it. Link out to related wiki pages and
  back to any `raw/` source.
- **Shipping something** (a report, plan, draft, deliverable) →
  `outputs/YYYY-MM-DD-slug.md`, `type: output`.
- **After any of the above**: add the page to `index.md`, append one line
  to `log.md`.

## Naming

- `raw/` and `outputs/` filenames: `YYYY-MM-DD-slug.md`.
- `wiki/` filenames: `Topic Name.md` (the title, spaces allowed) — the
  filename and the `title` frontmatter field should match so wikilinks
  resolve without a lookup table.

## Special raw/ subfolders read by the HUD

The terminal HUD (`hud/`) reads these live — treat them as regular
`raw/` pages (frontmatter, write-once) with one extra body convention:

- `raw/schedule/YYYY-MM-DD.md` — today's time blocks, one per line:
  `- HH:MM label`. The HUD highlights whichever block's time has most
  recently passed. No end times; the next line's start time ends the
  previous block implicitly.
- `raw/vitals/<metric-slug>.md` — one file per tracked number, body
  lines `- <timestamp> <value>`, appended over time (never rewritten).
  The HUD shows the last value plus a sparkline of recent points. Give
  it a `title` in frontmatter — that's the label shown on the panel.
