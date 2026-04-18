import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

basedir = os.path.abspath(os.path.dirname(__file__))


def _resolve_secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    raise RuntimeError(
        'SECRET_KEY environment variable is required. '
        'Copy .env.example to .env and set a secure value, '
        'or export SECRET_KEY before starting the app.'
    )


def _resolve_database_uri():
    url = os.environ.get('DATABASE_URL')
    if not url:
        return 'sqlite:///' + os.path.join(os.path.dirname(basedir), 'instance', 'inachalle.db')
    # Render / Heroku-style postgres:// → SQLAlchemy 2.x expects postgresql://
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


def _bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    DEBUG = False
    TESTING = False

    # Flask-Mail: 未設定時は送信をスキップ（mail_service.send_notification_email 参照）
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = _bool_env('MAIL_USE_TLS', True)
    MAIL_USE_SSL = _bool_env('MAIL_USE_SSL', False)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        'noreply@inachalle.jp',
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MAIL_SUPPRESS_SEND = True
    MAIL_SERVER = 'localhost'  # ensure mail.send path executes in tests


_CONFIG_BY_NAME = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config():
    name = os.environ.get('FLASK_ENV', 'production').lower()
    return _CONFIG_BY_NAME.get(name, ProductionConfig)
