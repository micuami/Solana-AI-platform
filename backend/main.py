from flask import Flask
from flask_restx import Api
from flask_migrate import Migrate
from exts import db
from models import AIDatabase, User
import os
from flask_jwt_extended import JWTManager
from databases import databases_ns
from auth import auth_ns


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)
    migrate = Migrate(app, db)
    JWTManager(app)

    api = Api(app, doc='/docs')

    api.add_namespace(databases_ns)
    api.add_namespace(auth_ns)

    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db, 
            'AIDatabase': AIDatabase, 
            'user': User
        }
    
    return app


