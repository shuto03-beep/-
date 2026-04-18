"""本番デプロイ時のDB初期化スクリプト。

挙動:
- テーブルが存在しない場合、create_all() で作成
- SEED_ON_BOOT=1 かつ School テーブルが空なら seed データを投入

Render の preDeployCommand から実行することを想定。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.school import School


def main():
    app = create_app()
    with app.app_context():
        print('Creating database tables if missing...')
        db.create_all()

        if os.environ.get('SEED_ON_BOOT') == '1' and not School.query.first():
            print('SEED_ON_BOOT=1 and DB is empty — running seed...')
            from seeds.seed_data import seed
            seed()
        else:
            print('Skipping seed.')

    print('DB init complete.')


if __name__ == '__main__':
    main()
