# backend/main.py
import os
from flask import Flask, jsonify
from flask_restx import Api
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from backend.externals import db
from backend.constants import UPLOAD_FOLDER
from backend.admin_initialization import ensure_admin_exists

migrate = Migrate()  # instanță globală

def create_app(config=None):
    """
    Create and configure the Flask app.
    - If `config` is provided, it must be a config class or object.
    - If not provided, we try to import DevConfig from configuration_classes_for_flask.
      If that fails, we fall back to a local sqlite DB so migrations / local dev work.
    """
    app = Flask(__name__, instance_relative_config=False)

    # Load config
    if config:
        app.config.from_object(config)
    else:
        try:
            from backend.configuration_classes_for_flask import DevConfig
            app.config.from_object(DevConfig)
        except Exception as e:
            # Helpful debug print and fallback to sqlite for local dev/migrations
            print("Warning: could not import DevConfig:", e)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
            fallback_db = "sqlite:///" + os.path.join(project_root, "dev.db")
            app.config.setdefault("SQLALCHEMY_DATABASE_URI", fallback_db)
            app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
            app.config.setdefault("DEBUG", True)

    # Initialize extensions that need app.config set first
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    JWTManager(app)

    # Ensure upload folder exists
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        print("Warning: could not create upload folder:", e)

    # Register routes / namespaces inside try/except to avoid import-time issues during migrations
    try:
        api = Api(app, doc="/docs")

        # import namespaces lazily to avoid circular import issues
        from backend.user_authentification import auth_ns
        # try to import optional namespaces; if one fails, continue (so migrations still work)
        try:
            from backend.ai_model_api_endpoints import models_ns
            api.add_namespace(models_ns)
        except Exception as e:
            print("Warning: could not import models_ns (AI model endpoints):", e)

        try:
            from backend.ai_databse_api_endpoints import databases_ns
            api.add_namespace(databases_ns)
        except Exception as e:
            print("Warning: could not import databases_ns (AI database endpoints):", e)

        api.add_namespace(auth_ns)
    except Exception as e:
        # non-fatal: allow app to be created for CLI/migrations even if API registration failed
        print("Warning: failed to register API namespaces:", e)

    # Shell context (useful for `flask shell`)
    @app.shell_context_processor
    def make_shell_context():
        ctx = {"db": db}
        # add models if available
        try:
            from backend.models import AIDatabase, User, AIModel
            ctx.update({"AIDatabase": AIDatabase, "User": User, "AIModel": AIModel})
        except Exception:
            try:
                from backend.models import AIDatabase, User
                ctx.update({"AIDatabase": AIDatabase, "User": User})
            except Exception:
                pass
        return ctx

    # Create minimal home route
    @app.route("/")
    def home():
        return jsonify({"message": "Welcome to Solana AI Platform"})

    # On first app start in dev, ensure admin exists (safe to call; uses app.app_context)
    try:
        with app.app_context():
            # prefer migrations, but if db tables don't exist, ensure_admin_exists may handle creation
            ensure_admin_exists()
    except Exception as e:
        # do not raise: we still want to allow migrations and CLI operations
        print("Warning: ensure_admin_exists failed at startup:", e)

    return app
# create_app can be called with a config class, e.g. create_app(ProdConfig) for production