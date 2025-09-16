from flask_restx import Resource, Namespace, fields
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask import Flask, request, jsonify

auth_ns = Namespace('auth', description='A name space for Authentication')


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
        'username': fields.String(required=True),
        'password': fields.String(required=True),
    }
)



@auth_ns.route('/signup')
class SignUp(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        data = request.get_json()

        username = data.get('username')

        db_user = User.query.filter_by(username=username).first()
        if db_user:
            return jsonify({"message":f"User with username {username} already exists."})

        new_user = User(
            username = data.get('username'),
            email = data.get('email'),
            password = generate_password_hash(data.get('password'))  
        )
        new_user.save()

        return jsonify({"message": "User created successfully."})
    
@auth_ns.route('/login')
class Login(Resource):

    @auth_ns.expect(login_model)
    def post(self):
        data = request.get_json()

        username = data.get('username')
        password = data.get('password')

        db_user = User.query.filter_by(username=username).first()
        if db_user and check_password_hash(db_user.password, password):

            access_token = create_access_token(identity=db_user.username)
            refresh_token = create_refresh_token(identity=db_user.username)

            return jsonify({"access token": access_token, "refresh token": refresh_token})
            
        return jsonify({"message": "Invalid username or password"}), 401