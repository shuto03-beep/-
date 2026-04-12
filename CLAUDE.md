# LLM Knowledge Base — 運用ガイド

## ディレクトリ構造

```
raw/          ← 未加工の素材（articles, papers, repos, datasets, assets）
wiki/
  sources/    ← ソース要約（raw → sources の1:1対応）
  concepts/   ← 概念ページ（トピック単位）
  entities/   ← エンティティページ（人物・組織）
  syntheses/  ← 統合分析ページ
  outputs/    ← クエリ結果の保存
  attachments/← 画像・添付ファイル
  glossary.md ← 用語索引（検索の高速化・表記揺れ防止）
  index.md    ← 全ページのインデックス
  log.md      ← 変更ログ
templates/    ← ページテンプレート
```

## 命名規則

- ファイル名: **kebab-case** (例: `deep-learning-basics.md`)
- 内部リンク: `[[ファイル名]]` 形式（拡張子なし）
- 日付: YYYY-MM-DD

## 4つの操作

### Ingest (`/wiki-ingest`)
raw/ の未処理ファイルを検出し、sources/ に要約を作成。
概念・エンティティを抽出して該当ページを作成/更新。
**必ず glossary.md を参照し、既存用語との表記揺れを防止すること。**

### Compile (`/wiki-compile`)
index.md・glossary.md を再構築。リンク検証・重複統合・整合性修復。

### Query (`/wiki-query [質問]`)
**glossary.md → Grep → 対象ファイルのみ Read** の2段階検索で回答。
必要に応じて raw/ の原文も参照。結果を outputs/ に保存。

### Lint (`/wiki-lint`)
壊れたリンク・glossary不整合・表記揺れ・矛盾・古い情報を検出し自動修正。

## 品質基準

| 種別 | 語数 | 備考 |
|------|------|------|
| ソース要約 | 200–500語 | 原文の忠実な要約 |
| 概念ページ | 500–1500語 | 複数ソースの統合 |
| エンティティ | 200–800語 | 事実ベース |

## ページ作成閾値

- **2ソース以上**: フルページとして作成
- **1ソースのみ**: スタブ（`status: stub`）として作成
- スタブは追加ソースが見つかり次第、フルページに昇格

## テンプレート

- `templates/source-summary.md` — ソース要約用
- `templates/concept-page.md` — 概念ページ用

## 表記揺れ防止

- Ingest 時は必ず `wiki/glossary.md` を先に読み、既存用語と照合する
- 同義語はエイリアスとして glossary に登録し、ページを分裂させない
- 英語は小文字 kebab-case に統一、略語と正式名称は両方登録

## 変更記録

全ての操作結果は `wiki/log.md` に日時・操作・対象・詳細を記録すること。
