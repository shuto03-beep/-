---
title: 変更ログ
type: log
---

# Wiki 変更ログ

<!-- エントリは /wiki-ingest と /wiki-compile により先頭に追記される -->

## 2026-04-12 — /wiki-compile 第2回: リンク修復 + ページ拡充 + ヘルスチェック
- **エイリアス修正11件**: 重複名を正規名に統一（bukatsu-chiiki-tenkai→bukatsu-chiiki-ikou、shogai-gakushu-ka→shougai-gakushuu-ka 等）
- **概念ページ8件を新規作成**: ai-voice-recorder, game-play-kazoku, juekisha-futan-model, ai-replacing-work, recording-and-productivity, harness-engineering, yuusen-junitsuke, work-life-balance
- **エンティティ7件を新規作成**: kyouiku-ka, kakogawa-shi, claude-ai, chuutairen, inami-chuugakkou, kobe-shi, meitantei-conan
- **スタブ7件をdraftに昇格**: coaching-shiko, claude-ai, haruma, kakogawa-shi, kyouiku-ka, mizuno-fuku-kacho, plaud-device
- **ヘルスレポート**: 117ページ / stub率16.3% / 孤立ページ0件
- **index.md を完全再構築**: 被参照数付きの全ページ一覧

## 2026-04-12 — /wiki-compile: シンセシス3本を生成
- **[[inachalle-vs-senkou-jirei]]**: いなチャレをつくば市（みどりのSCC・茎崎中KCSC）、渋谷区（渋谷ユナイテッド）、スポーツ庁ガイドラインと比較分析。「KCSCからSCCへの段階的進化」を稲美町の理想パスとして提示。3つの即時アクション（生徒アンケート、月謝基準値、補助金総点検）を提案
- **[[shigoto-katei-shiko-framework]]**: 職場（指導設計、部活動地域展開）と家庭（子どもの学習、家庭菜園、ゲーム）に共通する思考フレームワーク（コーチング、フィードバック設計、プロジェクト管理、エッセンシャリズム）を発見。「観察→分解→設計→委譲」の4層構造を抽出
- **[[ai-gyousei-katsuyou]]**: Plaudライフログ→Claude→ナレッジベースの実践から、行政AI活用の3ステージ（プロンプト→コンテキスト→ハーネスエンジニアリング）と部活動地域展開への具体適用を分析

## 2026-04-12 — 外部記事 Ingest（部活動地域移行関連）
- **raw/articles/ に4件の記事を取得・保存**:
  - スポーツ庁ガイドライン（2025年12月公表、予算139億円、「地域展開」への名称変更）
  - つくば市先行事例（みどりのSCC完全移行モデル、茎崎中KCSC学校主導モデル）
  - 渋谷区「渋谷ユナイテッド」（生徒アンケート、11クラブ、子どもファースト理念）
  - 稲美町「いなチャレ」公式情報統合（近隣6自治体比較含む）
- **wiki/sources/ に4件のソースページを作成**
- **[[bukatsu-chiiki-ikou]] 概念ページを更新**: 全国の先行事例セクションを追加
- **index.md を更新**: 外部記事ソース4件、アウトプット1件を追加

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
