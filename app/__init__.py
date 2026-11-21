from pathlib import Path
from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(test_config=None):
    root_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=str(root_dir / "static"),
        template_folder=str(Path(__file__).resolve().parent / "templates"),
    )
    app.config.from_object("app.config.Config")
    if test_config:
        app.config.update(test_config)
    if str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite:"):
        # SQLite in-memory tests use StaticPool, which rejects PostgreSQL pool
        # sizing options configured for serverless production connections.
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["AI_MODEL_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.reports import reports_bp
    from app.routes.issues import issues_bp
    from app.routes.admin import admin_bp
    from app.routes.map import map_bp
    from app.routes.analytics import analytics_bp
    from app.routes.ai import ai_bp
    from app.routes.pages import pages_bp
    from app.routes.public_map import public_map_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(public_map_bp)
    app.register_blueprint(health_bp)

    from app.utils.security import ensure_csrf_token
    from app.utils.api import error

    @app.before_request
    def enforce_read_only_demo_session():
        if (
            session.get("demo_login")
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.path not in {
                "/api/auth/logout", "/api/auth/login", "/api/auth/register",
                "/api/auth/demo-login", "/api/auth/admin-demo-login",
            }
        ):
            return error("Demo accounts are read-only. Sign in as a citizen to submit or edit reports.", status=403)

    @app.context_processor
    def inject_security_helpers():
        return {"csrf_token": ensure_csrf_token()}

    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    if not app.config.get("SKIP_DB_INIT", False):
        with app.app_context():
            db.create_all()
            from app.services.seed_service import ensure_seed_categories_and_settings
            ensure_seed_categories_and_settings()

    return app
