# Render.com 無料デプロイ手順

このガイドに沿えば **約15〜30分** で `https://inachalle-xxxx.onrender.com` のような公開URLで動作確認できるようになります。

## 必要なもの

- GitHubアカウント（既にお持ち）
- Render.com アカウント（次で作成・無料）

## 無料プランの制限

| 項目 | 無料プランの制限 |
|------|----------------|
| Webサービス | 15分無操作でスリープ（初回アクセスに30秒程度） |
| PostgreSQL | 作成から**90日後に自動削除** |
| データ容量 | 1GB |
| 月あたり実行時間 | 750時間まで（1サービスなら無制限相当） |

**→ 動作確認・デモ用途には十分。本番運用には有料プラン（約$7/月〜）推奨**

---

## 手順

### 1. Renderアカウント作成（2分）
1. https://render.com/ を開く
2. 「Get Started for Free」→ GitHubで認証
3. 無料プランなのでクレジットカード不要

### 2. リポジトリをRenderに接続（3分）
1. Renderダッシュボード右上の「**New +**」→「**Blueprint**」
2. 「Connect a repository」で GitHub の `shuto03-beep/-` を選択
3. ブランチは `main` か `claude/coding-skills-reference-exhXv` を指定
   - ※ 未マージならまず main にマージするのがおすすめ
4. Render が `render.yaml` を自動検出

### 3. Blueprint のデプロイ承認（5分）
1. 「Apply」をクリック
2. Render が以下を自動作成:
   - Web サービス (`inachalle`)
   - PostgreSQL データベース (`inachalle-db`)
   - `SECRET_KEY` 環境変数（自動生成）
   - `DATABASE_URL`（DB → Webサービスへ自動接続）
3. 初回ビルド開始 → **10〜15分待つ**（pip install + DB初期化 + seed投入）

### 4. 完了
ダッシュボードにWebサービスの公開URLが表示される:
```
https://inachalle-xxxx.onrender.com
```
初回アクセスは**30秒程度**かかります（スリープ解除）。

---

## 初期ログイン情報

seed データが自動投入されているので、以下7アカウントで即ログイン可能:

| ロール | ユーザー名 | パスワード |
|--------|-----------|-----------|
| 事務局 | `admin` | `admin123` |
| 学校担当 | `school_inami` | `school123` |
| 認定団体代表 | `tanaka` | `tanaka123` |
| 一般団体代表 | `suzuki` | `suzuki123` |
| 一般住民 | `yamada` | `yamada123` |
| 指導者 | `coach_ito` | `coach123` |
| 保護者 | `parent_sato` | `parent123` |

⚠️ **本番用途では必ずパスワードを変更してください**（admin でログイン後、`/admin/users` から）。

---

## カスタムドメイン（任意・後でOK）

`https://inachalle.town-inami.jp` のような独自ドメインにする場合:
1. Render Web サービスの「Settings」→「Custom Domain」
2. DNSの CNAME を `inachalle-xxxx.onrender.com` に向ける
3. 自動で Let's Encrypt SSL が発行される

---

## メール送信を有効化する（任意）

Plaud会議でも要望のあった通知メールを送る場合:

Render ダッシュボード → Web サービス → Environment → 以下を追加:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=アプリパスワード（2段階認証で取得）
MAIL_DEFAULT_SENDER=your-gmail@gmail.com
```

追加後「Save, Rebuild, and Deploy」。

---

## コード更新時の自動デプロイ

GitHubに push するたびに Render が自動で再デプロイします。
preDeploy で `scripts/init_db.py` が走り、新しいテーブルは自動作成されますが、**既存テーブルの列追加/型変更** は手動マイグレーションが必要です（フェーズ4候補: Flask-Migrate 整備）。

---

## トラブルシューティング

### 「Application failed to respond」が続く
- ダッシュボード → Logs タブでエラーを確認
- よくある原因: `SECRET_KEY` 未設定 → Environmentで手動追加

### データベースが90日で消える
- 無料Postgres は90日制限。延命する場合:
  - 有料プラン ($7/月) にアップグレード
  - または定期的に新DBを作って seed から再構築

### 初回アクセスが30秒かかる
- 無料プランのスリープ。常時起動したい場合は Cron で定期Ping、または有料プラン

---

## 他の無料選択肢

Render 以外にも:
- **Railway.app** — $5/月分の無料クレジット
- **Fly.io** — 3つまで無料VM + 3GB persistent disk（SQLite保持可）
- **PythonAnywhere** — 無料Flask枠あり（UI操作）

必要ならこれらのガイドも作成します。
