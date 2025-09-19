from flask_restx import Namespace, Resource, fields
from backend.models import AIDatabase, User
from flask_jwt_extended import jwt_required
from flask import request
import os
from backend.config import Config
from backend.externals import db

UPLOAD_FOLDER = Config.UPLOAD_FOLDER

databases_ns = Namespace('databases', description='A namespace for AI Databases')

db_model = databases_ns.model(
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

# endpoint pentru baze de date
@databases_ns.route('/databases')
class DatabaseListResource(Resource):

    @databases_ns.marshal_list_with(db_model)
    def get(self):
        """ Return all databases """
        return AIDatabase.query.all()


@databases_ns.route('/databases/upload')
class DatabaseUploadResource(Resource):

    @databases_ns.marshal_with(db_model)
    @databases_ns.expect(db_model)
    @jwt_required()
    def post(self):
        """ Upload a new database file """
        file = request.form.get('file')
        name = request.form.get('name')
        model_name = request.form.get('model_name')
        purpose = request.form.get('purpose')
        description = request.form.get('description')
        user_id = request.form.get('user_id')  # ID-ul user-ului care incarca

        if not file or not name or not purpose or not user_id:
            return {"message": "No file, name, scope or user id was provided."}, 400

        # verificare daca user-ul exista
        user = db.session.get(User, user_id)
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


@databases_ns.route('/databases/<int:database_id>')
class DatabaseResource(Resource):

    @databases_ns.marshal_with(db_model)
    def get(self, database_id):
        """ Get data of a single database """
        return AIDatabase.query.get_or_404(database_id)

    @databases_ns.marshal_with(db_model)
    @databases_ns.expect(db_model)
    @jwt_required()
    def put(self, database_id):
        """ Update a database record """
        db_entry = AIDatabase.query.get_or_404(database_id)
        
        data = request.get_json()

        db_entry.update(**data)

        return db_entry, 200

    @jwt_required()
    def delete(self, database_id):
        """ Delete a database and its file """
        db_entry = AIDatabase.query.get_or_404(database_id)
        db_entry.delete()
        return {"message": "Database deleted successfully."}, 200