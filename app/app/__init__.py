from flask import Flask, redirect, url_for
from .config import Config
from .extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .routes.auth import auth_bp
    from .routes.articles import articles_bp
    from .routes.warehouses import warehouses_bp
    from .routes.bookings import bookings_bp
    from .routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(warehouses_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(reports_bp)

    @app.route('/')
    def index():
        return redirect(url_for('reports.stock'))

    return app
