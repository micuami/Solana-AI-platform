import os
import secrets
from backend.constants import BASE_DIR

from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('DEV_FALLBACK_SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
    SQLALCHEMY_ECHO = False

class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, 'dev.db')
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, 'test.db')
    TESTING = True

class ProdConfig(Config):
    SECRET_KEY = os.environ.get('PRODUCTION_KEY')
    if SECRET_KEY is None:
        raise ValueError("No SECRET_KEY set for production environment")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    DEBUG = False