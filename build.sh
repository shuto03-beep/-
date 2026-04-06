#!/usr/bin/env bash
# Render.com ビルドスクリプト
set -o errexit

pip install -r requirements.txt

# DB初期化 & シードデータ
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    from app.models.school import School
    if not School.query.first():
        from seeds.seed_data import seed
        seed()
    from seeds.demo_data import create_demo_data
    create_demo_data()
    print('DB setup complete')
"
