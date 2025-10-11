from flask import Flask, jsonify
from flask_restx import Api
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import os
from backend.externals import db
from backend.models import AIDatabase, User
from backend.ai_databse_api_endpoints import databases_ns
from backend.ai_model_api_endpoints import models_ns
from backend.user_authentification import auth_ns
from backend.constants import UPLOAD_FOLDER
from backend.admin_initialization import ensure_admin_exists

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)
    migrate = Migrate(app, db)
    JWTManager(app)

    with app.app_context():
        db.create_all()
        ensure_admin_exists()

    @app.route('/')
    def home():
        return jsonify({
            'message': 'Welcome to Solana AI Platform'
        })

    api = Api(app, doc='/docs')

    api.add_namespace(models_ns)
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
