# いなチャレ 動作確認ガイド

## 1. セットアップ（5分）

```bash
# 依存インストール
pip install -r requirements.txt

# 環境変数
cp .env.example .env
# .env を開いて SECRET_KEY を適当な文字列に設定（例: openssl rand -hex 32）
# 開発時は FLASK_ENV=development も追加

# データベース作成＆サンプル投入
python seeds/seed_data.py

# サーバー起動
python run.py
# → http://127.0.0.1:5000 で開く
```

起動後、以下7アカウントでログインして各画面を確認。

---

## 2. 確認チェックリスト

### 事務局（admin / admin123）
- [ ] `/dashboard` — 承認待ち/今日の予約/登録団体のカード
- [ ] `/admin/organizations` — 団体一覧・承認トグル
- [ ] `/admin/users` — ユーザー一覧
- [ ] `/admin/coaches` — 指導者一覧、ダブルカウント候補の黄ハイライト（小林）
- [ ] `/admin/coaches/new` — 指導者新規登録フォーム
- [ ] `/admin/coaches/dual-role-workload` — 教員兼職の週上限チェック（小林が対象）
- [ ] `/admin/reports` — 月次概要＋CSVダウンロードボタン群
- [ ] `/admin/reports/monthly` — 印刷用月報（ブラウザ印刷でPDF化）
- [ ] `/admin/activity-logs` — 監査ログ（seedでは空、操作後に増える）
- [ ] CSVダウンロード3種:
  - [ ] 予約明細CSV
  - [ ] 団体一覧CSV
  - [ ] 中体連参加名簿CSV（Excel で日本語が崩れない）

### 学校担当（school_inami / school123）
- [ ] `/dashboard` — 今日/今週/ブロックの3カード、7日分予約、クイックアクション
- [ ] `/blocks` — 学校ブロック一覧（運動会準備が表示）
- [ ] `/blocks/new` — ブロック追加フォーム

### 団体代表・認定（tanaka / tanaka123）
- [ ] `/dashboard` — いなチャレ認定バッジ＋今後の予約一覧
- [ ] `/reservations/new` — 新規予約、**3ヶ月先まで**日付選択可能
- [ ] カレンダーで自団体の予約が表示される

### 団体代表・一般（suzuki / suzuki123）
- [ ] `/reservations/new` — **1ヶ月先まで**しか選択不可（認定との差を確認）

### 指導者（coach_ito / coach123）
- [ ] ログイン後 `/dashboard` → `/my/dashboard` に自動リダイレクト
- [ ] プロフィール・所属団体・今後2週間の予定が表示
- [ ] `/my/compensation` — 期間指定で謝金見込み確認、合計が表示される

### 保護者（parent_sato / parent123）
- [ ] ログイン後 `/dashboard` → `/family/dashboard` に自動リダイレクト
- [ ] 子供の所属団体（いなみサッカークラブ）と活動予定
- [ ] 自分宛の通知（「今週末の練習について」）が表示

### 一般住民（yamada / yamada123）
- [ ] `/dashboard` — 施設閲覧と団体登録案内
- [ ] `/admin/register_organization` — 団体登録申請フォーム

---

## 3. アクセシビリティ確認
- [ ] タブキーでフォーカスが回る。アクセントカラーの太い枠が表示される
- [ ] `Tab` キー初押しで「本文へスキップ」リンクが画面左上に出現
- [ ] Ctrl/+ で文字拡大しても崩れない
- [ ] スマホ表示（DevToolsのデバイス切替）でボタンが44px以上
- [ ] OS設定で「動きを減らす」を ON にするとアニメーションが抑制される

---

## 4. 業務シナリオ演習

### シナリオA: 新団体を承認する
1. admin でログイン
2. `/admin/organizations` で未承認団体を選択（初期データでは無いのでまず一般住民 yamada でログインして団体登録申請 → admin で承認）
3. 承認後、活動ログに記録されているか `/admin/activity-logs` で確認
4. 承認メンバーへ通知が飛んでいるか確認

### シナリオB: 月報を作成する
1. admin で `/admin/reports/monthly` を開く
2. 対象月を選んで「印刷 / PDF保存」
3. ブラウザの「PDFとして保存」で実際に出力

### シナリオC: 中体連へ提出する認定クラブ名簿を作る
1. admin で `/admin/reports` を開く
2. 「中体連参加名簿」ボタンをクリック
3. Excel で開いて内容確認

### シナリオD: 教員兼職の活動時間をチェックする
1. admin で `/admin/coaches/dual-role-workload` を開く
2. 対象週を選び、小林先生が「超過」「注意」「余裕」のどれに該当するか確認
3. 予約を増やすと警告ステータスが変わることを確認

---

## 5. 既知の制約
- 現状 Coach → Reservation の直接リンクはなく、「所属団体の活動時間＝指導者の稼働時間」の概算です。実稼働との差分は事務局で調整。
- 学校ユーザーは `role='school'` の単一アカウントで、特定校への紐付けは未実装（`School.query.first()` で代表を取得）。
- メール送信は SMTP 未設定時はログのみ（本番では `.env` に MAIL_SERVER を設定）。
- 指導者・保護者アカウントの**セルフサインアップ**は未実装。事務局が手動で登録・紐付け。
