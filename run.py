from app import create_app
from app.extensions import db

app = create_app()

# 初回起動時にDB作成 & シードデータ投入
with app.app_context():
    db.create_all()
    from app.models.school import School
    if not School.query.first():
        from seeds.seed_data import seed
        seed()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
