# PythonAnywhere 無料デプロイ手順

所要時間: **約30分**
公開URL: `https://mizuno00303.pythonanywhere.com`

## 無料プランの制約と付き合い方

| 項目 | 制限 | 対策 |
|------|------|------|
| ディスク | 512MB | コードは軽量なので十分 |
| CPU秒数 | 100秒/日 | 通常の閲覧・予約程度なら超えない |
| 起動維持 | **3ヶ月ごとにワンクリック延長** | カレンダーに「90日後に延長」登録 |
| 独自ドメイン | 不可 | `mizuno00303.pythonanywhere.com` のまま運用 |
| バックグラウンド処理 | 不可 | 不要（メール送信は同期） |

---

## 手順

### ステップ1: PythonAnywhereにログイン
https://www.pythonanywhere.com/login/ で `mizuno00303` アカウントにログイン。

### ステップ2: Bashコンソールを開く
ダッシュボード → **Consoles** → **Bash** をクリック → 新しいコンソールが開く

### ステップ3: リポジトリをクローン
コンソールで以下を実行:
```bash
cd ~
git clone https://github.com/shuto03-beep/-.git
cd -
git checkout claude/coding-skills-reference-exhXv
```

※ main にマージ済みなら `git checkout main`

### ステップ4: 仮想環境を作成して依存インストール
```bash
mkvirtualenv --python=/usr/bin/python3.10 inachalle-venv
pip install -r requirements.txt
```

※ `psycopg2-binary` は PostgreSQL 不要なのでエラーが出ても無視してOK。SQLiteで動きます。

エラーが出る場合は個別インストール:
```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Flask-WTF \
    Werkzeug email-validator python-dotenv Flask-Mail gunicorn
```

### ステップ5: .env ファイル作成
```bash
cd ~/-
cp .env.example .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
echo "FLASK_ENV=production" >> .env
```

`.env` の中身を編集して、冒頭の `SECRET_KEY=change-me-...` 行は削除（ファイル末尾に追加した乱数のものを残す）:
```bash
nano .env
```

### ステップ6: DB初期化とサンプルデータ投入
```bash
mkdir -p instance
SECRET_KEY=$(grep SECRET_KEY .env | cut -d= -f2) SEED_ON_BOOT=1 python scripts/init_db.py
```

以下のようにログインアカウント一覧が出れば成功:
```
事務局管理者:       admin / admin123
指導者:             coach_ito / coach123
保護者:             parent_sato / parent123
...
```

### ステップ7: Webアプリ設定
1. ダッシュボード → **Web** タブ → **Add a new web app**
2. ドメイン: `mizuno00303.pythonanywhere.com` → Next
3. フレームワーク: **Manual configuration** → Next
4. Pythonバージョン: **Python 3.10** → Next

### ステップ8: WSGIファイル編集
Web タブの **Code** セクション:
- **Source code**: `/home/mizuno00303/-`
- **Working directory**: `/home/mizuno00303/-`
- **WSGI configuration file**: リンクをクリック → エディタが開く

エディタの中身を**全部削除**して、以下を貼り付け:
```python
import os
import sys

PROJECT_ROOT = '/home/mizuno00303/-'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from app import create_app
application = create_app()
```

保存（右上の Save）。

### ステップ9: Virtualenv 設定
Web タブの **Virtualenv** セクション:
- 入力欄に `/home/mizuno00303/.virtualenvs/inachalle-venv` と入力して保存

### ステップ10: 静的ファイル設定
Web タブの **Static files** セクション:
- URL: `/static/`
- Directory: `/home/mizuno00303/-/app/static/`

Enter で保存。

### ステップ11: リロードして起動
Web タブ上部の緑の **Reload** ボタンをクリック。

### ステップ12: 確認
ブラウザで https://mizuno00303.pythonanywhere.com を開く。
→ ログイン画面が表示されれば完了！

---

## 他の先生への案内テンプレート

A4で印刷して配布するか、LINE/メールで送ります:

```
━━━━━━━━━━━━━━━━━━━━━━━━━
いなチャレ施設予約システム（試験運用）
━━━━━━━━━━━━━━━━━━━━━━━━━

URL: https://mizuno00303.pythonanywhere.com

あなたのログイン情報:
  ユーザー名: （個別発行）
  初期パスワード: （個別発行）

初回ログイン後、「ユーザー設定」から必ず
パスワードを変更してください。

ご質問・不具合は事務局まで。
━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## メンテナンス

### 3ヶ月に1回（最重要）
PythonAnywhere にログイン → Web タブ → **"Run until 3 months from today"** ボタンをクリック
→ カレンダーに90日ごとのリマインダーを設定しておくこと

### コード更新時
```bash
cd ~/-
git pull
python scripts/init_db.py  # 新テーブル自動作成
```
Web タブで **Reload** をクリック。

### バックアップ（任意・推奨）
Bash コンソールで:
```bash
cp ~/-/instance/inachalle.db ~/backup-$(date +%Y%m%d).db
```
週1回程度実行してダウンロード。

### パスワードリセット
admin でログインして、`/admin/users/<ユーザーID>` から「有効/無効」切替や、
Bash コンソールで直接:
```bash
cd ~/-
source ~/.virtualenvs/inachalle-venv/bin/activate
python -c "
from app import create_app
from app.extensions import db
from app.models.user import User
app = create_app()
with app.app_context():
    u = User.query.filter_by(username='対象ユーザー名').first()
    u.set_password('新パスワード')
    db.session.commit()
"
```

---

## トラブルシューティング

### 「Something went wrong :-(」エラー
→ Web タブの **Error log** を確認。よくある原因:
- `.env` が未作成 → SECRET_KEY エラー
- Virtualenv のパスが違う
- `instance/inachalle.db` が書き込めない（権限確認）

### アプリが2週間ほど使われず止まった
→ 無料プランは20日以上アクセスがないと停止することがある。
   Web タブから Reload で復活。

### 先生たちの利用が多くて重い
→ 有料プラン（$5/月〜）にアップグレードするとCPU・帯域が増える。
