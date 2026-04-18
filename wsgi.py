"""PythonAnywhere WSGI エントリーポイント

PythonAnywhere の Web タブで以下に書き換える:

    import sys
    path = '/home/mizuno00303/-'
    if path not in sys.path:
        sys.path.insert(0, path)

    from dotenv import load_dotenv
    load_dotenv(f'{path}/.env')

    from app import create_app
    application = create_app()

このファイルはリポジトリ内のサンプルとして残しています。
実体は PythonAnywhere が管理する /var/www/mizuno00303_pythonanywhere_com_wsgi.py です。
"""
import os
import sys

# リポジトリのクローン先ディレクトリ（PythonAnywhereアカウント名に合わせて変更）
PROJECT_ROOT = os.path.expanduser('~/-')

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# .env を読み込む（SECRET_KEY など）
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
except ImportError:
    pass

from app import create_app  # noqa: E402

application = create_app()
