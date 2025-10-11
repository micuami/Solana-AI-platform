import os
import secrets
from backend.constants import BASE_DIR
from backend.helper_file_to_get_aws_secrets import get_secret
from dotenv import load_dotenv
load_dotenv()

def fetch_keys():
    try:
        return get_secret()
    except Exception as e:
        print(f"Warning: Could not fetch secrets from AWS Secrets Manager: {e}")
        return None
    
class Config:
    SECRET_KEY = fetch_keys().get('DEV_FALLBACK_SECRET_KEY') if fetch_keys() else secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
    SQLALCHEMY_ECHO = False

class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, 'dev.db')
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, 'test.db')
    TESTING = True

# class ProdConfig():
#     SECRET_KEY = fetch_keys().get('PRODUCTION_KEY') if fetch_keys() else None
#     if SECRET_KEY is None:
#         raise ValueError("No SECRET_KEY set for production environment")