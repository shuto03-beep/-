import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

# Windows対応: SQLiteはスラッシュ区切りが必要
db_path = os.path.join(instance_path, 'inachalle.db').replace('\\', '/')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'inachalle-dev-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + db_path
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
