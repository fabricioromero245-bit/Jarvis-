---
title: Vault Memory Layer
type: wiki
tags: [meta, system]
created: 2026-08-14
updated: 2026-08-14
summary: How this vault stores memory for the AI operating system — structure, rules, and conventions.
---

# Vault Memory Layer

This vault is the memory layer for the AI operating system: a plain
markdown store, no database, readable end to end in a text editor. The
full schema lives in `CLAUDE.md` at the vault root — this page is the
plain-language version, and the first entry in [[Index]].

## The three folders

- **`raw/`** holds capture, not understanding — transcripts, clips,
  dumps, exactly as they arrived. A raw file is written once and never
  edited; if something in it matters, that meaning gets distilled into a
  wiki page, which links back to the raw file as its source.
- **`wiki/`** holds understanding — one page per topic, rewritten in
  place as the topic is better understood. This page is an example: it
  will change if the vault's own rules change.
- **`outputs/`** holds what the system ships — reports, plans, drafts —
  each one dated in its filename and never edited after the fact.

## Why a graph instead of a folder tree

Pages link to each other with `[[wikilinks]]` by title. A topic's page
should link to the raw sources it was distilled from and to neighboring
wiki topics, rather than re-explaining them inline. Over time this turns
the vault into a graph of what the system knows, with `raw/` as the
evidence layer underneath it and `outputs/` as the record of what it
produced from that knowledge.

## Bookkeeping

Two files at the vault root keep the graph honest:

- [[Index]] lists every page with a one-line hook — it must stay in sync
  with the folder contents.
- The log (`log.md`) is an append-only history of changes to the vault —
  every new page, rewrite, or deletion gets one line, and old lines are
  never touched.
