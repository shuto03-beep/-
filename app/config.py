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


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'instance', 'inachalle.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
