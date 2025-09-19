import re
from flask_restx import Resource, Namespace, fields
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from flask import request, jsonify, make_response
from backend.models import User

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
    if verify_if_the_identifier_is_email(identifier): return User.query.filter_by(email=identifier).first()
    else: return User.query.filter_by(username=identifier).first()

@auth_ns.route('/signup')
class SignUp(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        data = request.get_json()

        username = data.get('username')
        email = data.get('email')

        if verify_if_user_or_email_exists(username):
            return jsonify({"message":f"User with username {username} already exists."}), 409

        if verify_if_user_or_email_exists(email):
            return jsonify({"message":f"User with email {email} already exists."}), 409

        new_user = User(
            username = data.get('username'),
            email = data.get('email'),
            password = generate_password_hash(data.get('password'))  
        )
        new_user.save()

        return make_response(jsonify({"message": "User created successfully."}), 201)
    
@auth_ns.route('/login')
class Login(Resource):

    @auth_ns.expect(login_model)
    def post(self):
        data = request.get_json()

        identifier = data.get('identifier')
        password = data.get('password')

        db_user = find_user_by_identifier(identifier)
        if db_user and check_password_hash(db_user.password, password):

            access_token = create_access_token(identity=db_user.username)
            refresh_token = create_refresh_token(identity=db_user.username)

            return jsonify({"access token": access_token, "refresh token": refresh_token})
            
        return jsonify({"message": "Invalid credentials"}), 401