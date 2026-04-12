# ナレッジベース設定

## フォルダ構成
- `knowledge-base/raw/` — 原本素材。AIは読み取り専用。記事・論文・リポジトリ・データセット・アセット。
- `knowledge-base/wiki/` — AI生成ナレッジ。要約・概念・エンティティ・出典・統合・インデックス。
- `knowledge-base/templates/` — 新規ページ用テンプレート。

## 命名規則
- 全ファイル: kebab-case のみ。例: `active-inference.md` ✅ `Active Inference.md` ❌
- 出典: `著者-年-短縮タイトル.md` (例: `friston-2010-free-energy.md`)

## 操作

### Ingest（取り込み）
1. `knowledge-base/raw/` 内の未処理ファイルを読み取る
2. 各ソースについて: `knowledge-base/wiki/sources/` に要約（200〜500語）を作成
3. 主要な概念を抽出 → `knowledge-base/wiki/concepts/` にページを作成・更新
4. エンティティ（人物・組織）を抽出 → `knowledge-base/wiki/entities/` にページを作成・更新
5. `knowledge-base/wiki/index.md` に新規エントリを追加
6. `knowledge-base/wiki/log.md` にタイムスタンプ付きで変更を記録

### Compile（整理・再構築）
1. 全wikiページから `knowledge-base/wiki/index.md` を再構築
2. 全 `[[wiki-links]]` が既存ページに解決されるか検証
3. 重複する概念をマージ
4. ページ間の相互参照を更新

### Query（検索・回答）
1. 全wikiページから関連コンテンツを検索
2. `[[出典]]` 付きで回答を返す
3. 内容が充実している場合は `knowledge-base/wiki/outputs/` に結果を保存

### Lint（品質チェック）
1. リンク切れの `[[wiki-links]]` を検出
2. ソース間の矛盾を検出
3. 古い情報（1年以上前のソース）をフラグ
4. 拡充が必要なスタブページを特定
5. カバレッジのギャップを報告

## 閾値
- 2つ以上のソースに登場する概念 → `knowledge-base/wiki/concepts/` にフルページ
- 1つのソースのみの概念 → スタブ（100語未満）
- 要約: 200〜500語
- 概念記事: 500〜1500語

## Wikiページフォーマット
```
# ページタイトル
<!-- tags: タグ1, タグ2 -->
<!-- updated: YYYY-MM-DD -->

## 概要
簡潔な説明。

## 詳細
[[wiki-links]] を使って関連概念への参照を含む本文。

## 出典
- [[ソースファイル名]]
```
