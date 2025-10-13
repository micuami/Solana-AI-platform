# backend/user_authentication.py
import re
from flask_restx import Resource, Namespace, fields
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (JWTManager,
create_access_token, create_refresh_token, jwt_required, get_jwt_identity,
get_jwt_identity)
from flask import request
from backend.models import User
from backend.strenght_of_a_password import validate_password

auth_ns = Namespace('auth', description='A namespace for Authentication')

signup_model = auth_ns.model(
    'SignUp',
    {
        'username': fields.String(required=True),
        'email': fields.String(required=True),
        'password': fields.String(required=True),
    }
)

login_model = auth_ns.model(
    'Login',
    {
        'identifier': fields.String(required=True, description='Username or Email'),
        'password': fields.String(required=True),
    }
)

def verify_if_user_or_email_exists(identifier):
    return User.query.filter((User.username == identifier) | (User.email == identifier)).first() is not None

def verify_if_the_identifier_is_email(identifier):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, identifier) is not None

def find_user_by_identifier(identifier):
    if verify_if_the_identifier_is_email(identifier):
        return User.query.filter_by(email=identifier).first()
    else:
        return User.query.filter_by(username=identifier).first()

@auth_ns.route('/signup')
class SignUp(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        data = request.get_json() or {}

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return {"message": "username, email and password are required"}, 400

        if verify_if_user_or_email_exists(username):
            return {"message": f"User with username {username} already exists."}, 409

        if verify_if_user_or_email_exists(email):
            return {"message": f"User with email {email} already exists."}, 409

        if not validate_password(password):
            return {"message": "Password does not meet the required criteria."}, 400

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        new_user.save()

        return {"message": "User created successfully.", "user_id": new_user.id}, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        data = request.get_json() or {}
        identifier = data.get('identifier')
        password = data.get('password')

        if not identifier or not password:
            return {"message": "identifier and password required"}, 400

        db_user = find_user_by_identifier(identifier)
        if db_user and check_password_hash(db_user.password, password):
            # use user.id as identity for robustness
            access_token = create_access_token(identity=str(db_user.id))
            refresh_token = create_refresh_token(identity=str(db_user.id))
            return {"access_token": access_token, "refresh_token": refresh_token, "user_id": db_user.id}, 200

        return {"message": "Invalid credentials"}, 401

@auth_ns.route('/me')
class MeResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user = User.query.get(identity)
        if not user:
            return {"message": "User not found"}, 404
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }, 200

auth_ns.route('/refresh')
class RefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        identity = get_jwt_identity()
        new_access_token = create_access_token(identity=identity)
        return {"access_token": new_access_token}, 200