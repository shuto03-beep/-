knowledge-base/CLAUDE.md を読み込み、設定を確認してください。その後、Ingest（取り込み）操作を実行:
1. `knowledge-base/raw/` 内で、まだ `knowledge-base/wiki/sources/` に参照されていないファイルをスキャン
2. 未処理のファイルごとに `knowledge-base/wiki/sources/` にソース要約を作成
3. 概念を抽出し、`knowledge-base/wiki/concepts/` にページを作成・更新
4. エンティティを抽出し、`knowledge-base/wiki/entities/` にページを作成・更新
5. `knowledge-base/wiki/index.md` を更新
6. `knowledge-base/wiki/log.md` に記録を追加
