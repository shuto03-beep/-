---
title: 変更ログ
type: log
---

# Wiki 変更ログ

<!-- エントリは /wiki-ingest と /wiki-compile により先頭に追記される -->

## 2026-04-12 — 初回 Ingest
- **ソースページ 79件作成** — raw/plaud/ の全 Plaud ライフログエントリを処理
  - 2026-03-28〜04-13 の音声記録から wiki/sources/ にソースページを生成
  - 約60件が draft（実質的な要約あり）、約19件が stub（内容が薄い/空の録音）
- **概念ページ 9件作成** — 複数ソースに跨がるキー概念を抽出
  - [[bukatsu-chiiki-ikou]]（部活動地域移行）: 最多参照（15+ソース）
  - [[katei-saien]]（家庭菜園）: 6ソース
  - [[community-school]]、[[kenshoku-kengyou]]、[[hojokin-unyou]]: 各5-6ソース
  - [[inachalle]]、[[coaching-shiko]]、[[companion-planting]]、[[lifelog-system]]: 各3-5ソース
- **エンティティページ 6件作成** — 頻出の人物・組織を構造化
  - [[shougai-gakushuu-ka]]（生涯学習課）: 最多参照（20+ソース）
  - [[kyouiku-iinkai]]、[[inami-chou]]、[[mizuno-fuku-kacho]]、[[haruma]]、[[plaud-device]]
- **index.md を再構築** — 全94ページの一覧を掲載

## 2026-04-12 — 初期化
- ナレッジベースを初期化
- 3層アーキテクチャを構築（raw/ → wiki/ → CLAUDE.md）
- テンプレートを作成（concept, source, entity, synthesis）
- スラッシュコマンドを作成（wiki-ingest, wiki-compile, wiki-query, wiki-lint）
