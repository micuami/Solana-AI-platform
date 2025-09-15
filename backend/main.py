from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_migrate import Migrate
from config import DevConfig
from exts import db
from models import AIDatabase, User
import os

app = Flask(__name__)
app.config.from_object(DevConfig)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

api = Api(app, doc='/docs')

db_model = api.model(
    'AIDatabase',
    {
        'id': fields.Integer(readOnly=True),
        'name': fields.String(required=True),
        'model_name': fields.String(),
        'purpose': fields.String(required=True),
        'file_path': fields.String(),
        'file_hash': fields.String(),
        'size_mb': fields.Float(),
        'description': fields.String(),
        'user_id': fields.Integer(required=True),
        'created_at': fields.String()
    }
)

user_model = api.model(
    'User',
    {
        'id': fields.Integer(readOnly=True),
        'username': fields.String(required=True),
        'email': fields.String(required=True),
    }
)

# endpoint pentru utilizatori
@api.route('/users')
class UserListResource(Resource):

    @api.marshal_list_with(user_model)
    def get(self):
        """ Return all users """
        return User.query.all()

    @api.expect(user_model)
    @api.marshal_with(user_model)
    def post(self):
        """ Create a new user """
        data = request.get_json()
        user = User(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password')
        )
        user.save()
        return user, 201



# endpoint pentru baze de date
@api.route('/databases')
class DatabaseListResource(Resource):

    @api.marshal_list_with(db_model)
    def get(self):
        """ Return all databases """
        return AIDatabase.query.all()


@api.route('/databases/upload')
class DatabaseUploadResource(Resource):

    @api.marshal_with(db_model)
    def post(self):
        """ Upload a new database file """
        file = request.files.get('file')
        name = request.form.get('name')
        model_name = request.form.get('model_name')
        purpose = request.form.get('purpose')
        description = request.form.get('description')
        user_id = request.form.get('user_id')  # ID-ul user-ului care incarca

        if not file or not name or not purpose or not user_id:
            return {"message": "No file, name, scope or user id was provided."}, 400

        # verificare daca user-ul exista
        user = User.query.get(user_id)
        if not user:
            return {"message": "The user does not exist"}, 404

        # salvare fisier pe disc
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # calcul hash si dimensiune
        file_hash = AIDatabase.calculate_hash(file_path)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # creare entry in DB
        db_entry = AIDatabase(
            name=name,
            model_name=model_name,
            purpose=purpose,
            file_path=file_path,
            file_hash=file_hash,
            size_mb=size_mb,
            description=description,
            user_id=user.id
        )
        db_entry.save()

        return db_entry, 201


@api.route('/databases/<int:id>')
class DatabaseResource(Resource):

    @api.marshal_with(db_model)
    def get(self, id):
        """  Get data of a single database """
        return AIDatabase.query.get_or_404(id)

    def delete(self, id):
        """ Delete a database and its file """
        db_entry = AIDatabase.query.get_or_404(id)
        db_entry.delete()
        return {"message": "Baza de date ștearsă"}, 200


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'AIDatabase': AIDatabase, 'User': User}


if __name__ == '__main__':
    app.run()
