CLAUDE.md を読んで、URL指定のIngest操作を実行してください。

取り込むURL: $ARGUMENTS

## 手順

### Step 1: URLからコンテンツを取得
- WebFetch ツールで指定URLの内容を取得する
- プロンプト: 「この記事のタイトル、著者、公開日、本文を全て抽出してください。本文は省略せず、見出し構造と共に忠実に保持してください」
- 403エラーなど取得失敗した場合は、WebSearch でタイトル・著者・概要を収集するフォールバックに切り替える

### Step 2: raw/articles/ に保存
- ファイル名: `{著者kebab-case}-{年}-{タイトル短縮kebab-case}.md`
  - 例: `tanaka-2026-ai-agent-design`
  - 著者不明の場合: `{ドメイン}-{年}-{タイトル短縮}.md`
- ファイルの先頭に `Source: {元URL}` を追加
- 取得した本文を Markdown 形式で保存

### Step 3: 通常のIngestフローを実行
- `/wiki-ingest` と同じ手順で以下を実行:
  1. `wiki/glossary.md` を読み既存用語を把握
  2. `wiki/sources/` にソース要約を作成（200-500語、重要引用を含む）
  3. 概念を抽出し、既存用語と照合の上 `wiki/concepts/` に追加/更新
  4. エンティティを抽出し `wiki/entities/` に追加/更新
  5. `wiki/glossary.md` を更新
  6. `wiki/index.md` と `wiki/log.md` を更新

## ルール

- ファイル名は kebab-case
- 著者名・日付がURLから取得できない場合は、ドメイン名と推定年を使う
- 本文取得が失敗した場合、ユーザーに「テキストを貼り付けてください」と依頼する
- raw/ に保存した元ファイルも git 管理対象とする

## 出力

取り込みが完了したら、以下をサマリーとして表示:
- 取得元URL
- raw/ に保存したファイル名
- 作成した source / concepts / entities
- 発見した既存概念との関連
