# life_v2 — Cognitive Continuity Partner

Plaud Lifelog **V2**。
Plaud V1（`plaud_lifelog/`）が「録音 → 文字起こし → 構造化」を担うのに対し、
V2 は「**構造化 → 即実行**」の最後の1マイルだけを担う。

> あなたの最大のボトルネックは「能力・構想」と「実行」の乖離である。
> V2 は **分析を披露しない**。**カレンダーに登録できる JSON** と
> **1分以内に押せるボタン** だけを返す。

---

## 設計の4つの軸

| # | 名前 | 何を解決するか |
|---|---|---|
| 1 | **Cognitive Friction Reduction** | 分析 → 実行の摩擦をゼロに。出力は常にカレンダー登録可能な JSON ＋ 承認用 Yes/No のみ |
| 2 | **Self-Aesthetic Distillation** | 内的スコアカード4軸を時系列蓄積し、「あなただけの美学」を統計的に抽出 |
| 3 | **Triage as a Service** | オープンタスク全件を「高価値 / 低価値」に強制仕分け（捨てる決断を AI が代行） |
| 4 | **Three-Beat Rhythm** | 朝（仕込み）/ 夜（採点）の2拍子を毎日のレールに |

## 高価値タスクの定義（3フィルタ）

`life_v2` が「Next Action」として認める唯一の条件は、以下のうち **1つ以上に合致** すること:

- **leverage** — 一度の労力が未来の時間を生む（仕組み化・テンプレ化）
- **mission** — 教育環境の再構築（いなチャレ等）、家族の知的成長に直結
- **uniqueness** — メタ認知 / AI活用 / 哲学思考を持つこのユーザーにしかできない

3つのうち1つも該当しない場合、それは **必ず dropped に流れる**（ユーザーは決断不要）。

## 内的スコアカード（4軸 × 各10点）

| 軸 | 意図 |
|---|---|
| `systemize` | 未来の自分を楽にするシステムを作ったか |
| `declutter` | 他者期待ベースの低価値タスクを切り捨てられたか |
| `two_handed` | 片手間ではない深い集中の時間を取れたか |
| `knowledge_share` | 家族や周囲と知的な発見を共有できたか |

「他者からの評価」は採点項目に含めない。
他者評価は `aesthetic.json` の **データ** として淡々と参照するだけ。

---

## セットアップ

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-xxxxx       # 未設定時はヒューリスティック動作
export LIFE_V2_AI_MODEL=claude-sonnet-4-5   # 任意
export LIFE_V2_DISCORD_WEBHOOK_URL=...      # 任意（PLAUD_DISCORD_WEBHOOK_URL も可）
export LIFE_V2_DAILY_BUDGET=180             # 1日の高価値タスク予算（分）
export LIFE_V2_MAX_ACTIONS=3                # Next Action の最大本数
```

---

## 使い方

### 1. coach — メイン機能

```bash
# 直接テキスト
python -m life_v2 coach --text "今日の予定..." --save --save-scorecard

# Plaud V1 のエントリから
python -m life_v2 coach --entry 2026-04-26_asa-kai --save

# Plaud entries 直近1日分をまとめて
python -m life_v2 coach --recent-days 1 --save --save-scorecard --notify

# stdin 経由
cat memo.txt | python -m life_v2 coach --from-stdin

# カレンダー登録用 JSON / .ics を書き出す
python -m life_v2 coach --recent-days 1 --calendar-json out.json --ics out.ics
```

出力は4ブロック固定:

1. **📊 内的スコアカード評価** — 4軸 × 10点 + 短評
2. **🗑️ 捨てるべきタスク（戦略的撤退）** — disposition: drop / automate / delegate / defer
3. **⚡ Next Actions** — 最大3件、各タスクに L/M/U フラグ + duration_minutes + priority
4. **```json ... ```** — そのままカレンダー登録スクリプトに貼り付け可能

### 2. triage — オープンタスクの強制振り分け

```bash
python -m life_v2 triage           # Plaud V1 の tasks.json から
python -m life_v2 triage --json    # JSON で他ツールに連携
```

最大 **5件のみ** 高価値として残し、残りは全て dropped に流す（reason 付き）。

### 3. morning — 朝の仕込み

```bash
python -m life_v2 morning --save --notify
```

昨日のスコアカード + Plaud 直近1日のテキスト → 「今日の意図 / 90分ブロック / 捨てる候補 / 家族と共有する種」。

`preflight` には「通知をオフにする」「机の上を空にする」など **物理動作** が必ず含まれる。

### 4. evening — 夜の決算

```bash
python -m life_v2 evening --save --save-scorecard --notify
```

今日のテキスト → 4軸採点 + `tomorrow_first_move`（明日カレンダーで押す1ボタン）。
反省や精神論は出力しない。データと動作のみ。

### 5. distill — 美学の蒸留

```bash
python -m life_v2 distill --days 30 --save
```

過去30日のスコアカードから:

- `aesthetic_principles` — あなたが内的に尊んでいる原則3つ
- `strongest_axis` / `weakest_axis` — 統計的に強い軸 / 影の軸
- `next_self_experiment` — 影の軸を埋めるための明日の自己実験1つ

### 6. history — 履歴サマリ

```bash
python -m life_v2 history --days 30
```

各軸の平均・最大・最小・トレンド（前半 vs 後半の差分）を表示。

---

## データレイアウト

```
data/life_v2/
├── scorecards/
│   └── 2026-04-26.json      # evening / coach --save-scorecard で蓄積
├── triage/
│   └── 2026-04-26_coach.json
├── rituals/
│   ├── 2026-04-26_morning.json
│   └── 2026-04-26_evening.json
└── aesthetic.json           # distill --save で更新
```

Plaud V1 の `data/plaud/entries/` と `data/plaud/tasks.json` は **読み取り専用** で参照する。
両者のデータは混ざらず、独立してバージョン管理できる。

---

## GitHub Actions による自動運用

`.github/workflows/life_v2_daily.yml` で以下を自動実行:

- **JST 06:30** — `morning --notify` + `coach --recent-days 1 --notify`
- **JST 22:00** — `evening --notify`（日曜のみ `distill --save` も実行）

必要な Secrets:

- `ANTHROPIC_API_KEY` — Claude 用
- `LIFE_V2_DISCORD_WEBHOOK_URL` または `PLAUD_DISCORD_WEBHOOK_URL`

---

## 仕様プロンプト（参考）

`life_v2.prompts` モジュールに、Cognitive Continuity Partner のシステムプロンプトが
そのまま定義されている。プロンプト本文を変更したい場合は
`life_v2/prompts.py` を編集すれば、`coach` / `triage` / `distill` / `morning` /
`evening` の挙動が連動して変わる。

## フォールバック動作

`ANTHROPIC_API_KEY` 未設定または API 失敗時:

- `coach` — 箇条書き / `TODO:` 形式の行を抽出し、3フィルタのキーワード辞書で振り分け
- スコアカード — 仕組み・断捨離・集中・共有のシグナル単語の出現頻度から **保守的に** 採点
- distill — 過去履歴の単純集計でラベル付け

API がなくても **CLI は止まらない**。これは「実行への摩擦をゼロにする」設計原則の一部。
