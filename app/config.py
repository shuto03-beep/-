import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

# Windows対応: SQLiteはスラッシュ区切りが必要
db_path = os.path.join(instance_path, 'inachalle.db').replace('\\', '/')

# Render等のPaaSはDATABASE_URLにpostgres://を使うがSQLAlchemyはpostgresql://が必要
database_url = os.environ.get('DATABASE_URL', 'sqlite:///' + db_path)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'inachalle-dev-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
