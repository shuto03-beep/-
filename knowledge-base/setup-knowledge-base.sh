#!/bin/bash
# ============================================================
# LLM Knowledge Base — Obsidian Vault 初期セットアップスクリプト
# ============================================================
# 使い方:
#   1. このファイルを任意の場所に保存
#   2. ターミナルで実行: bash setup-knowledge-base.sh [vault-path]
#   3. 例: bash setup-knowledge-base.sh ~/Documents/my-knowledge-base
# ============================================================

VAULT_PATH="${1:-$HOME/my-knowledge-base}"

echo "🧠 LLM Knowledge Base セットアップ開始..."
echo "📁 Vault パス: $VAULT_PATH"
echo ""

# --- Vault ルートディレクトリ ---
mkdir -p "$VAULT_PATH"

# --- Layer 1: raw/ (元素材) ---
mkdir -p "$VAULT_PATH/raw/articles"
mkdir -p "$VAULT_PATH/raw/papers"
mkdir -p "$VAULT_PATH/raw/repos"
mkdir -p "$VAULT_PATH/raw/datasets"
mkdir -p "$VAULT_PATH/raw/assets"

# --- Layer 2: wiki/ (AI生成Wiki) ---
mkdir -p "$VAULT_PATH/wiki/concepts"
mkdir -p "$VAULT_PATH/wiki/entities"
mkdir -p "$VAULT_PATH/wiki/sources"
mkdir -p "$VAULT_PATH/wiki/syntheses"
mkdir -p "$VAULT_PATH/wiki/outputs"
mkdir -p "$VAULT_PATH/wiki/attachments"

# --- templates/ ---
mkdir -p "$VAULT_PATH/templates"

# --- .claude/commands/ (スラッシュコマンド用) ---
mkdir -p "$VAULT_PATH/.claude/commands"

# --- index.md ---
cat > "$VAULT_PATH/wiki/index.md" << 'EOF'
# Knowledge Base Index
<!-- updated: $(date +%Y-%m-%d) -->

## Concepts
_No concepts yet. Run Ingest to populate._

## Entities
_No entities yet._

## Sources
_No sources yet. Add files to `raw/` and run Ingest._
EOF

# --- log.md ---
cat > "$VAULT_PATH/wiki/log.md" << 'EOF'
# Change Log

| Date | Operation | Details |
|------|-----------|---------|
EOF

# --- CLAUDE.md ---
cat > "$VAULT_PATH/CLAUDE.md" << 'CLAUDE_EOF'
# Knowledge Base Configuration

## Structure
- `raw/` — Source of truth. Read-only for AI. Articles, papers, repos, datasets, assets.
- `wiki/` — AI-generated knowledge. Summaries, concepts, entities, sources, syntheses, indexes.
- `templates/` — Templates for new pages.

## Naming
- All files: kebab-case only. Example: `active-inference.md` ✅ `Active Inference.md` ❌
- Sources: `author-year-short-title.md` (e.g. `friston-2010-free-energy.md`)

## Operations

### Ingest
1. Read new/unprocessed files in `raw/`
2. For each source: create summary (200-500 words) in `wiki/sources/`
3. Extract key concepts → create/update pages in `wiki/concepts/`
4. Extract entities (people, orgs) → create/update pages in `wiki/entities/`
5. Update `wiki/index.md` with new entries
6. Log changes in `wiki/log.md` with timestamp

### Compile
1. Rebuild `wiki/index.md` from all wiki pages
2. Verify all `[[wiki-links]]` resolve to existing pages
3. Merge duplicate concepts
4. Update cross-references between pages

### Query
1. Search across all wiki pages for relevant content
2. Return answer with `[[source]]` citations
3. Save query result in `wiki/outputs/` if substantial

### Lint
1. Find broken `[[wiki-links]]`
2. Detect contradictions between sources
3. Flag outdated information (>1 year old sources)
4. Identify stub pages needing expansion
5. Report gaps in coverage

## Thresholds
- Concept in 2+ sources → full page in `wiki/concepts/`
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
CLAUDE_EOF

# --- スラッシュコマンド: /wiki-ingest ---
cat > "$VAULT_PATH/.claude/commands/wiki-ingest.md" << 'EOF'
Read CLAUDE.md for configuration. Then execute the Ingest operation:
1. Scan `raw/` for files not yet referenced in `wiki/sources/`
2. For each unprocessed file, create a source summary in `wiki/sources/`
3. Extract and create/update concept pages in `wiki/concepts/`
4. Extract and create/update entity pages in `wiki/entities/`
5. Update `wiki/index.md`
6. Append to `wiki/log.md`
EOF

# --- スラッシュコマンド: /wiki-compile ---
cat > "$VAULT_PATH/.claude/commands/wiki-compile.md" << 'EOF'
Read CLAUDE.md for configuration. Then execute the Compile operation:
1. Scan all files in `wiki/`
2. Rebuild `wiki/index.md` with all concepts, entities, sources
3. Verify all [[wiki-links]] resolve
4. Merge any duplicate pages
5. Update cross-references
6. Log changes in `wiki/log.md`
EOF

# --- スラッシュコマンド: /wiki-query ---
cat > "$VAULT_PATH/.claude/commands/wiki-query.md" << 'EOF'
Read CLAUDE.md for configuration. Then execute the Query operation:
The user will ask a question after this command.
1. Search across all wiki/ pages for relevant content
2. Synthesize an answer with [[source]] citations
3. If the answer is substantial, save it in `wiki/outputs/`
4. Suggest related concepts the user might want to explore
EOF

# --- スラッシュコマンド: /wiki-lint ---
cat > "$VAULT_PATH/.claude/commands/wiki-lint.md" << 'EOF'
Read CLAUDE.md for configuration. Then execute the Lint operation:
1. Find all broken [[wiki-links]]
2. Detect contradictions between sources
3. Flag pages with outdated info
4. Identify stub pages that could be expanded
5. Report coverage gaps
6. Fix issues automatically where possible
7. Log all changes in `wiki/log.md`
EOF

# --- テンプレート: ソース要約 ---
cat > "$VAULT_PATH/templates/source-summary.md" << 'EOF'
# {{title}}
<!-- tags:  -->
<!-- updated: {{date}} -->
<!-- source: {{url}} -->

## Summary


## Key Concepts
- [[concept-name]]

## Notable Quotes


## My Notes

EOF

# --- テンプレート: 概念ページ ---
cat > "$VAULT_PATH/templates/concept-page.md" << 'EOF'
# {{title}}
<!-- tags:  -->
<!-- updated: {{date}} -->

## Summary


## Details


## Related Concepts
- [[related-concept]]

## Sources
- [[source-name]]
EOF

# --- .obsidian 設定（グラフビュー用） ---
mkdir -p "$VAULT_PATH/.obsidian"

echo ""
echo "✅ セットアップ完了!"
echo ""
echo "📂 作成されたフォルダ構造:"
find "$VAULT_PATH" -type d | head -30 | sed "s|$VAULT_PATH|.|g" | sort
echo ""
echo "📝 作成されたファイル:"
find "$VAULT_PATH" -type f -name "*.md" | sed "s|$VAULT_PATH|.|g" | sort
echo ""
echo "🚀 次のステップ:"
echo "  1. Obsidian でこの Vault を開く: $VAULT_PATH"
echo "  2. raw/articles/ に記事やメモを追加"
echo "  3. Claude Code で Vault ディレクトリに移動: cd $VAULT_PATH"
echo "  4. Ingest 実行: /wiki-ingest"
echo ""
