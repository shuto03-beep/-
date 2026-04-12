# Knowledge Base Configuration

## Structure
- `knowledge-base/raw/` — Source of truth. Read-only for AI. Articles, papers, repos, datasets, assets.
- `knowledge-base/wiki/` — AI-generated knowledge. Summaries, concepts, entities, sources, syntheses, indexes.
- `knowledge-base/templates/` — Templates for new pages.

## Naming
- All files: kebab-case only. Example: `active-inference.md` ✅ `Active Inference.md` ❌
- Sources: `author-year-short-title.md` (e.g. `friston-2010-free-energy.md`)

## Operations

### Ingest
1. Read new/unprocessed files in `knowledge-base/raw/`
2. For each source: create summary (200-500 words) in `knowledge-base/wiki/sources/`
3. Extract key concepts → create/update pages in `knowledge-base/wiki/concepts/`
4. Extract entities (people, orgs) → create/update pages in `knowledge-base/wiki/entities/`
5. Update `knowledge-base/wiki/index.md` with new entries
6. Log changes in `knowledge-base/wiki/log.md` with timestamp

### Compile
1. Rebuild `knowledge-base/wiki/index.md` from all wiki pages
2. Verify all `[[wiki-links]]` resolve to existing pages
3. Merge duplicate concepts
4. Update cross-references between pages

### Query
1. Search across all wiki pages for relevant content
2. Return answer with `[[source]]` citations
3. Save query result in `knowledge-base/wiki/outputs/` if substantial

### Lint
1. Find broken `[[wiki-links]]`
2. Detect contradictions between sources
3. Flag outdated information (>1 year old sources)
4. Identify stub pages needing expansion
5. Report gaps in coverage

## Thresholds
- Concept in 2+ sources → full page in `knowledge-base/wiki/concepts/`
- Concept in 1 source → stub (< 100 words)
- Summaries: 200-500 words
- Concept articles: 500-1500 words

## Wiki Page Format
```
# Page Title
<!-- tags: tag1, tag2 -->
<!-- updated: YYYY-MM-DD -->

## Summary
Brief overview.

## Details
Main content with [[wiki-links]] to related concepts.

## Sources
- [[source-file-name]]
```
