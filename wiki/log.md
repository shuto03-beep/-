# 変更ログ

| Date | Action | Target | Details |
|------|--------|--------|---------|
| 2026-04-12 | Ingest | yamamoto-2026-macd-swing-strategy | raw/articles/ から取り込み。ソース要約作成。概念: macd, rsi, swing-trade, divergence, bollinger-band, atr, risk-management, backtesting, nikkei225。エンティティ: yamamoto-kenichi |
| 2026-04-12 | Ingest | suzuki-2025-rsi-divergence | raw/articles/ から取り込み。ソース要約作成。概念: rsi, divergence, macd, swing-trade, bollinger-band, atr, risk-management, backtesting。エンティティ: suzuki-miho, j-welles-wilder |
| 2026-04-12 | Ingest | nikkei225-sector-performance-2025 | raw/datasets/ からCSVを取り込み。データ概要の要約作成。概念: nikkei225, sharpe-ratio(stub), sector-analysis(stub) |
| 2026-04-12 | Create | glossary.md | 初回構築。概念11件、エンティティ3件、ソース3件を登録 |
| 2026-04-12 | Update | index.md | 初回構築。全ページをカテゴリ別にリスト化 |
| 2026-04-12 | Compile | glossary.md | 文字化け(mojibake)を修正。6箇所の破損文字を復元 |
| 2026-04-12 | Compile | 全体 | 整合性チェック完了。壊れたリンク0件、重複0件、Raw参照全件一致 |
| 2026-04-12 | Query | macd-rsi-combined-strategy-effectiveness | 「MACDとRSI併用戦略の有効性」を検索。glossary→Grep→5ファイル読み込みで回答生成。outputs/に保存 |
| 2026-04-12 | Lint | index.md | outputs/macd-rsi-combined-strategy-effectiveness がindex未登録 → 自動追加 |
| 2026-04-12 | Lint | 全体 | 全チェック完了。壊れたリンク0、glossary不整合0、矛盾0、古い情報0、未処理ソース0、原文参照切れ0。自動修正1件 |
| 2026-04-12 | Ingest | mext-2025-bukatsu-chiiki-tenkai-guideline | Web検索で情報収集→raw/articles/に保存→ソース要約作成。概念: bukatsu-chiiki-tenkai(stub), chiiki-club-nintei-seido(stub), kyouin-hatarakikata-kaikaku(stub), shoshika-taiou(stub)。エンティティ: monbukagakusho, sports-cho |
