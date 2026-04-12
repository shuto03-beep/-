CLAUDE.md を読んで、Compile操作を実行してください。

## 手順

### Step 1: 整合性チェック（エラー回復）
- wiki/sources/ に存在するが wiki/index.md に載っていないファイルを検出 → 追加
- wiki/concepts/, wiki/entities/ に存在するが wiki/glossary.md に未登録のエントリ → glossary に追加
- wiki/glossary.md に登録されているが対応ファイルがないエントリ → 警告表示
- raw/ にファイルがあり wiki/sources/ にもあるが、source の `Raw:` パスが一致しないもの → 修正

### Step 2: インデックス再構築
- wiki/index.md をゼロから再構築
- concepts, entities, sources, syntheses, outputs をカテゴリ別にリスト化
- 各エントリに一行説明を付与（glossary.md から取得）

### Step 3: glossary.md 再構築
- wiki/ 内の全概念・エンティティ・ソースから glossary.md を再構築
- 既存のエイリアス情報は保持する
- 一行説明が欠けているエントリは各ファイルの冒頭から生成

### Step 4: リンク検証
- 全ての `[[wiki-links]]` が実在するファイルを指しているか検証
- 壊れたリンクを報告し、可能なら最も近い既存ファイル名を提案

### Step 5: 重複統合
- 同一の概念やエンティティを扱う重複ページがあれば統合を提案・実行
- glossary.md のエイリアスも統合後の名前に更新

### Step 6: クロスリファレンス更新
- 各ページの「関連概念」「関連ソース」セクションを最新の状態に更新

### Step 7: ログ記録
- wiki/log.md に変更内容を記録

## 出力

変更したファイルの一覧と、検出した問題のサマリーを表示してください。
修復が必要だった整合性の問題は特に明記してください。
