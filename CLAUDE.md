# CLAUDE.md — リポジトリ & ナレッジベース設定

## リポジトリ構成
- Flask 施設予約アプリ: app/
- トレーディングボット: main.py, signals.py, data/state.json
- Plaud ライフログ: plaud_lifelog/, data/plaud/
- ナレッジベース: raw/, wiki/, templates/

## KB 3層アーキテクチャ
- **Layer 1 (raw/)**: 元素材。読み取り専用。AI は絶対に書き換えない
- **Layer 2 (wiki/)**: AI が生成・維持する統合 Wiki
- **Layer 3 (本ファイル)**: スキーマと操作手順

## Wiki ディレクトリ
- concepts/ — 概念・フレームワーク（500-1500語）
- entities/ — 人物・組織・プロジェクト（200-500語）
- sources/ — ソースごとの要約ページ（200-500語）
- syntheses/ — 3つ以上のソースを横断する分析
- outputs/ — 成果物・レポート・意思決定記録

## 命名規則
- ファイル名: ケバブケース ASCII（例: companion-planting.md）
- タイトル: H1 に自然言語（日本語 OK）
- リンク: [[kebab-case-filename]]（拡張子なし）
- Plaud エントリ: 既存の YYYY-MM-DD_slug 形式を維持

## ページ閾値
- 2つ以上のソースが参照 → フルページ化
- 1つのソースのみ → スタブ（frontmatter に `status: stub`）
- 3つ以上のソース → シンセシス候補

## Frontmatter（必須）
```yaml
title: ページタイトル
type: concept | entity | source | synthesis | output
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: stub | draft | review | final
sources: []
tags: []
```

## 操作サイクル
### Ingest: raw/ の新素材を処理
1. raw/ の未処理ファイルをスキャン
2. wiki/sources/ にソースページを作成
3. 概念を抽出 → concepts/ を作成・更新
4. エンティティを抽出 → entities/ を作成・更新
5. index.md と log.md を更新

### Compile: Wiki を構築・更新
1. 全ページの相互参照を検証
2. 3つ以上のソース参照を持つ概念 → シンセシス作成
3. index.md をページ一覧で再構築
4. 全 [[リンク]] の解決を確認

### Query: 引用付きで質問に回答
1. wiki/ 内を横断検索
2. [[page-name]] リンクで出典を明示
3. 確信度とギャップを報告

### Lint: 健康チェック
1. 壊れた [[リンク]] を検出
2. 14日以上更新のないスタブをフラグ
3. ページ間の矛盾を検出
4. 孤立ページ（被リンクゼロ）を報告

## Plaud 統合
- data/plaud/entries/ の JSON → raw/plaud/ に Markdown エクスポート
- 各エントリをソースとして Wiki に取り込み可能
- エクスポートコマンド: `python -m plaud_lifelog export --all -o raw/plaud/`

## 品質基準
- 要約: 200-500語 / 概念記事: 500-1500語
- 全ての主張にソースページへのリンク必須
- 日本語で記述する
