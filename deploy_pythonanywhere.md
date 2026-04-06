# PythonAnywhere デプロイ手順

## 1. アカウント作成（2分）
1. https://www.pythonanywhere.com にアクセス
2. 「Start running Python online in less than a minute!」→ **「Create a Beginner account」**
3. ユーザー名・メール・パスワードを設定（ユーザー名がURLになる）

## 2. コードをアップロード（3分）
1. ログイン後、右上の **「Consoles」** タブ → **「Bash」** をクリック
2. 黒い画面（ターミナル）が開くので、以下を **1行ずつ貼り付けて実行**：

```
git clone https://github.com/shuto03-beep/- inachalle
cd inachalle
git checkout claude/school-reservation-system-9XwA3
pip install --user -r requirements.txt
python run.py
```

「初期データを投入しました！」と表示されたら **Ctrl+C** で停止。

## 3. Webアプリ設定（3分）
1. 上部メニューの **「Web」** タブをクリック
2. **「Add a new web app」** → **「Next」**
3. **「Manual configuration」** を選択 → **「Python 3.10」** → **「Next」**

### 3a. ソースコードのパス設定
- **Source code:** `/home/あなたのユーザー名/inachalle`
- **Working directory:** `/home/あなたのユーザー名/inachalle`

### 3b. WSGIファイル編集
- 「WSGI configuration file」のリンクをクリック
- 中身を **全て削除** して、以下を貼り付け：

```python
import sys
import os

project_home = '/home/あなたのユーザー名/inachalle'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import create_app
from app.extensions import db

application = create_app()

with application.app_context():
    db.create_all()
    from app.models.school import School
    if not School.query.first():
        from seeds.seed_data import seed
        seed()
    from seeds.demo_data import create_demo_data
    create_demo_data()
```

**「あなたのユーザー名」を実際のユーザー名に置き換えてください！**

### 3c. 保存して起動
- **「Save」** → 上部の緑ボタン **「Reload」** をクリック

## 4. 完了！
ブラウザで以下にアクセス：
```
https://あなたのユーザー名.pythonanywhere.com
```

### ログイン情報
| ロール | ユーザー名 | パスワード |
|---|---|---|
| 事務局（管理者） | admin | admin123 |
| 団体責任者（認定） | tanaka | tanaka123 |
| 一般住民 | yamada | yamada123 |

## コード更新時
Consoles → Bash で：
```
cd inachalle && git pull origin claude/school-reservation-system-9XwA3
```
Web タブで **「Reload」** をクリック。
