# plaud-lifelog

Plaud Web が書き出した Word ファイル（文字起こし＋要約）を入力に、
Claude でライフログ（日記風ナラティブ + タグ + キーポイント）とタスク分析を
自動生成する CLI ツール。データは JSON ファイルとして `data/plaud/` 以下に保存される。

## セットアップ

```bash
pip install -r requirements.txt
# もしくは最小構成:
pip install python-docx anthropic

export ANTHROPIC_API_KEY=sk-ant-xxxxx     # 未設定ならフォールバックで動作
export PLAUD_AI_MODEL=claude-sonnet-4-5   # 任意
export PLAUD_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...   # 通知用（任意）
```

## 使い方

### 取り込み

```bash
# 単一ファイル
python -m plaud_lifelog ingest path/to/2026-04-11_朝会.docx

# フォルダ一括
python -m plaud_lifelog ingest path/to/plaud_exports/
python -m plaud_lifelog ingest path/to/plaud_exports/ -r   # サブフォルダも再帰

# 既存IDを上書き
python -m plaud_lifelog ingest path/to/file.docx --force
```

- Word からタイトル・収録日・要約・文字起こしを自動抽出
- Claude に 2 回問い合わせ、ライフログとタスク抽出を別々に生成
- `data/plaud/entries/<YYYY-MM-DD>_<slug>.json` に保存
- `data/plaud/index.json` と `data/plaud/tasks.json` を更新

ディレクトリを指定すると `.docx` を一括取り込み（`~$` で始まる Word 一時
ファイルはスキップ）。同じ ID のエントリが既に存在する場合はスキップし、
`--force` で再取り込み。`--dry-run` を付けると保存せず結果だけ表示する。

### タイムライン

```bash
python -m plaud_lifelog list
python -m plaud_lifelog list --limit 5
```

### タスク一覧

```bash
python -m plaud_lifelog tasks           # オープンのみ
python -m plaud_lifelog tasks --all     # 完了含む
```

優先度 (high → medium → low)、期限順に並ぶ。

### エントリ詳細

```bash
python -m plaud_lifelog show 2026-04-11_asa-kai
```

### メモ追記

Claude が生成したライフログに、あとから自分の主観を上書き追記する。

```bash
python -m plaud_lifelog note 2026-04-11_asa-kai "田中さんはリリース前で少し疲れていた"
cat memo.txt | python -m plaud_lifelog note 2026-04-11_asa-kai --stdin
```

- エントリ JSON に `notes: [{id, text, created_at}]` として追記（上書きはしない）
- `show` で JSON として表示される
- `export --entry <id>` の Markdown では `### メモ` セクションに箇条書き
- 存在しないエントリIDはエラー終了

### タスクの完了・再オープン

```bash
python -m plaud_lifelog mark t_20260411_01            # done にする（デフォルト）
python -m plaud_lifelog mark t_20260411_01 --open     # open に戻す
```

`tasks.json` と対応するエントリ JSON の両方の `status` を同期更新する。

### 統計サマリー

```bash
python -m plaud_lifelog stats            # 整形表示
python -m plaud_lifelog stats --json     # 生の JSON（外部処理向け）
python -m plaud_lifelog stats --analyze  # Claude で傾向分析コメントを追加
```

全エントリを走査して以下を集計する:

- エントリ総数 / 収録期間
- タスク total / done / open / 完了率 / 優先度内訳
- タグ TOP10 / カテゴリ TOP10 / 気分の出現頻度
- **月次推移** — 月ごとのエントリ数・タスク数・完了数・完了率

`--analyze` を付けると、集計データを Claude に渡して「全体所感 / 観察 /
次にやると良いこと」の3要素を JSON で生成する。APIキー未設定時は
ローカルのヒューリスティック（完了率・主要タグ・月次差分）で代替する。

### 全文検索

```bash
python -m plaud_lifelog search 提案書
python -m plaud_lifelog search 田中 --limit 5
```

- エントリの title / headline / narrative / tags / 要約 / 文字起こし / タスク名 を
  走査し、最初にヒットしたフィールドと前後 40 字のスニペットを表示する
- 新しい順に最大 `--limit` 件

### Markdown エクスポート

```bash
python -m plaud_lifelog export --entry 2026-04-11_asa-kai
python -m plaud_lifelog export --entry 2026-04-11_asa-kai -o out.md
python -m plaud_lifelog export --report 2026-04-05_to_2026-04-11
python -m plaud_lifelog export --report 2026-04-05_to_2026-04-11 -o weekly.md
python -m plaud_lifelog export --all                     # 全エントリ一括 → data/plaud/export_md/
python -m plaud_lifelog export --all -o ~/obsidian/plaud/ # Obsidian Vault へ書き出し
```

- エントリはメタ情報 / ライフログ本文 / タスク / 原文（要約・文字起こし）の
  順に整形される
- レポートはサマリー / ハイライト / 次の注力 / タグ集計 / エントリ一覧 /
  タスクサマリーで構成される
- narrative やメモの中の `@<entry_id>` 参照は自動的に Obsidian 風の
  `[[<entry_id>]]` リンクに変換される
- `--all` は全エントリを個別ファイルとして指定ディレクトリに書き出す
  （Obsidian Vault にそのまま投入可能）
- `-o` 省略時はエントリ/レポートは標準出力、`--all` は `data/plaud/export_md/`

### 週次 / 月次レポート

指定期間のエントリを集約し、Claude でライフログを俯瞰する振り返り
（要約 / ハイライト / 次の注力テーマ）を生成する。

```bash
python -m plaud_lifelog report                 # 直近 7 日
python -m plaud_lifelog report --days 14       # 直近 14 日
python -m plaud_lifelog report --from 2026-04-05 --to 2026-04-11
python -m plaud_lifelog report --month 2026-04 # 月初〜月末を自動範囲
python -m plaud_lifelog report --dry-run       # 保存せず結果だけ表示
```

`data/plaud/reports/<period>.json` に保存され、期間内のタグ集計・
気分集計・オープンタスク上位も含まれる。

#### Discord webhook への自動投稿

```bash
export PLAUD_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
python -m plaud_lifelog report --days 7 --notify
```

- 投稿内容はサマリー / ハイライト / 次の注力 / タグ / オープンタスク上位5件
- Discord の 2000 文字上限に合わせて自動分割
- webhook 未設定時はコンソールにプレビュー出力してスキップ（エラーにしない）
- `report --dry-run --notify` で JSON 保存せず投稿だけ行うことも可能

## GitHub Actions による自動運用

### 日次 inbox 取り込み（`.github/workflows/plaud_inbox.yml`）

`data/plaud/inbox/` に .docx ファイルを push するだけで、翌朝 JST 06:00
(= UTC 21:00) に自動的に ingest され、生成されたエントリが
`data/plaud/entries/` にコミットされる。

```
data/plaud/inbox/       ← ここに Plaud Web の Word を追加
  └── 2026-04-12_meeting.docx
```

- サブフォルダ対応（`-r` 付きで走査）
- inbox 配下の生 docx は `.gitignore` で除外されるためリポジトリには残らない
- 既存IDは自動スキップ、`--force` 相当の上書きはしないので安全

### 週次自動配信（`.github/workflows/plaud_weekly.yml`）

毎週月曜 JST 07:00 (= UTC 22:00 日曜) に `report --days 7 --notify`
を自動実行する。

セットアップ手順:

1. GitHub リポジトリの Settings → Secrets and variables → Actions で以下を登録
   - `ANTHROPIC_API_KEY`: Claude 用 API キー（未設定時はフォールバック経路で動作）
   - `PLAUD_DISCORD_WEBHOOK_URL`: Discord の webhook URL
2. 初回は Actions タブから workflow_dispatch で手動実行して動作確認
3. 生成されたレポートは `data/plaud/reports/<period>.json` に自動コミットされる

ワークフローは concurrency group `plaud-weekly` で自己シリアライズされ、
同居するトレードBot (`.github/workflows/run.yml`) とは完全に独立して動く。

## データレイアウト

```
data/plaud/
├── entries/
│   └── 2026-04-11_asa-kai.json
├── reports/
│   └── 2026-04-05_to_2026-04-11.json   # report コマンドで生成
├── index.json    # タイムライン（id, title, recorded_at, headline, tags, task_count）
└── tasks.json    # 全エントリから集約したタスク（priority, due, status など）
```

## Word 解析のルール

- 最初の 80 字以内の非空段落をタイトルとみなす（無ければファイル名）
- 本文冒頭の `YYYY-MM-DD` / `YYYY/MM/DD` / `YYYY年MM月DD日` を収録日として検出
- 「要約」「Summary」「文字起こし」「Transcript」などの見出しで要約と全文を分離
- 見出しが無い場合は全文を文字起こしとして扱う

## AI フォールバック

`ANTHROPIC_API_KEY` が未設定、もしくは Claude 呼び出しが失敗した場合は、
タイトルと要約冒頭のみを使った最小限のエントリを生成する。
その場合 `lifelog.source == "fallback"` が記録される。
