from flask import Flask
from app.config import get_config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.calendar import calendar_bp
    from app.routes.reservations import reservations_bp
    from app.routes.blocks import blocks_bp
    from app.routes.admin import admin_bp
    from app.routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(blocks_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)

    @app.errorhandler(404)
    def not_found(e):
        return '<h1>404 - ページが見つかりません</h1><p><a href="/">トップへ戻る</a></p>', 404

    @app.errorhandler(403)
    def forbidden(e):
        return '<h1>403 - アクセス権限がありません</h1><p><a href="/">トップへ戻る</a></p>', 403

    return app
