"""
PythonAnywhere用 WSGI設定ファイル

設定手順:
1. 「あなたのユーザー名」を実際のPythonAnywhereユーザー名に置換
2. Web タブの WSGI configuration file にこの内容をコピー
3. Save → Reload
"""
import sys
import os

# ★ ユーザー名を変更してください ★
project_home = '/home/あなたのユーザー名/inachalle'

if project_home not in sys.path:
    sys.path.insert(0, project_home)
os.chdir(project_home)

# run.py がDB初期化も含めて全て処理
from run import app as application
