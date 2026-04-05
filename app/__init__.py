from flask import Flask
from app.config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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

    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        from app.services.notification_service import get_unread_count
        if current_user.is_authenticated:
            return {'unread_count': get_unread_count(current_user.id)}
        return {'unread_count': 0}

    @app.errorhandler(404)
    def not_found(e):
        return '<h1>404 - ページが見つかりません</h1><p><a href="/">トップへ戻る</a></p>', 404

    @app.errorhandler(403)
    def forbidden(e):
        return '<h1>403 - アクセス権限がありません</h1><p><a href="/">トップへ戻る</a></p>', 403

    return app
