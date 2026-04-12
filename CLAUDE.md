# CLAUDE.md — Project Instructions for AI Sessions

## Repository Overview

This repo contains three main systems:

1. **Trading Bot** — Python scripts at root (`main.py`, `signals.py`, etc.) + Flask web app (`app/`)
2. **Plaud Lifelog** — CLI tool in `plaud_lifelog/` with data in `data/plaud/`
3. **Knowledge Base** — `raw/`, `wiki/`, and root-level `templates/` (markdown)

> **Note:** `templates/` at repo root contains markdown templates for the knowledge base.
> `app/templates/` contains HTML templates for Flask. These are completely separate.

## Knowledge Base

### Structure

- `raw/` — Source of truth. **Read-only for AI.** Articles, papers, repos, datasets, assets.
- `wiki/` — AI-generated knowledge. Summaries, concepts, entities, sources, syntheses, indexes.
- `templates/` — Markdown templates for new wiki pages.

### Naming Conventions

- All KB files use **kebab-case** only. Example: `active-inference.md`
- Source pages: `author-year-short-title.md` (e.g., `friston-2010-free-energy.md`)

### Page Format

Every wiki page uses this structure:

```markdown
---
tags: [tag1, tag2]
updated: YYYY-MM-DD
---

# Title

## Summary
(200-500 words)

## Details
(Use [[wiki-links]] to connect pages)

## Sources
- [[author-year-short-title]]
```

### Thresholds

- Concept appears in **2+ sources** → full page (500-1500 words in Details)
- Concept appears in **1 source** → stub (<100 words in Details)
- All summaries: 200-500 words

### Operations

#### Ingest

Process new files in `raw/` into wiki pages:

1. Read new/unprocessed files in `raw/`
2. For each source: create summary (200-500 words) in `wiki/sources/` using `templates/source.md`
3. Extract key concepts → create/update pages in `wiki/concepts/` using `templates/concept.md`
4. Extract entities (people, orgs) → create/update pages in `wiki/entities/` using `templates/entity.md`
5. Update `wiki/index.md` with new entries
6. Log changes in `wiki/log.md` with timestamp

#### Compile

Rebuild indexes and verify integrity:

1. Rebuild `wiki/index.md` from all wiki pages
2. Regenerate all files in `wiki/indexes/` (all-concepts, all-sources, all-entities, tag-index)
3. Verify all `[[wiki-links]]` resolve to existing pages
4. Merge duplicate concepts
5. Update cross-references between pages

#### Query

Search the wiki and return answers with citations:

1. Search across all wiki pages for relevant content
2. Return answer with `[[source]]` citations
3. Save query result in `wiki/outputs/` if substantial

#### Lint

Find and report problems:

1. Find broken `[[wiki-links]]`
2. Detect contradictions between sources
3. Flag outdated information (>1 year old sources)
4. Identify stub pages needing expansion (appear in 2+ sources now)
5. Report gaps in coverage
