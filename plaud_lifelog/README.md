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
```

## 使い方

### 取り込み

```bash
python -m plaud_lifelog ingest path/to/2026-04-11_朝会.docx
```

- Word からタイトル・収録日・要約・文字起こしを自動抽出
- Claude に 2 回問い合わせ、ライフログとタスク抽出を別々に生成
- `data/plaud/entries/<YYYY-MM-DD>_<slug>.json` に保存
- `data/plaud/index.json` と `data/plaud/tasks.json` を更新

`--dry-run` を付けると保存せず結果だけ表示する。

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

### タスクの完了・再オープン

```bash
python -m plaud_lifelog mark t_20260411_01            # done にする（デフォルト）
python -m plaud_lifelog mark t_20260411_01 --open     # open に戻す
```

`tasks.json` と対応するエントリ JSON の両方の `status` を同期更新する。

### 週次レポート

直近 7 日間のエントリを集約し、Claude でライフログを俯瞰する振り返り
（要約 / ハイライト / 次の注力テーマ）を生成する。

```bash
python -m plaud_lifelog report                 # 直近 7 日
python -m plaud_lifelog report --days 14       # 直近 14 日
python -m plaud_lifelog report --from 2026-04-05 --to 2026-04-11
python -m plaud_lifelog report --dry-run       # 保存せず結果だけ表示
```

`data/plaud/reports/<period>.json` に保存され、期間内のタグ集計・
気分集計・オープンタスク上位も含まれる。

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
