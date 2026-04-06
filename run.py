import sys
import os

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)

from app import create_app
from app.extensions import db

app = create_app()

# ローカル実行時のみDB初期化（本番はbuild.shで実行）
if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            from app.models.school import School
            if not School.query.first():
                from seeds.seed_data import seed
                seed()
            from seeds.demo_data import create_demo_data
            create_demo_data()
    except Exception as e:
        print(f'DB初期化エラー: {e}')
        print(f'DB URI: {app.config["SQLALCHEMY_DATABASE_URI"]}')
        sys.exit(1)

    print('\n========================================')
    print('  いなチャレ施設予約システム 起動中...')
    print('  http://localhost:5000 をブラウザで開いてください')
    print('  停止: Ctrl+C')
    print('========================================\n')
    app.run(debug=True, host='0.0.0.0', port=5000)
