from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request, current_app
from werkzeug.utils import secure_filename
import os
import hashlib

from backend.models import AIDatabase, User
from backend.externals import db
from backend.constants import UPLOAD_FOLDER

databases_ns = Namespace('databases', description='A namespace for AI Databases')

db_model = databases_ns.model(
    'AIDatabase',
    {
        'id': fields.Integer(readOnly=True),
        'name': fields.String(required=True),
        'model_name': fields.String(),
        'purpose': fields.String(required=True),
        'storage_uri': fields.String(),    # updated name
        'data_hash': fields.String(),      # updated name
        'merkle_root': fields.String(),
        'size_mb': fields.Float(),
        'description': fields.String(),
        'user_id': fields.Integer(required=True),
        'created_at': fields.String()
    }
)

# helper: merkle root by chunking file (returns hex string)
def merkle_root_from_file(path, chunk_size=4 * 1024 * 1024):
    def sha256_bytes(b):
        return hashlib.sha256(b).digest()

    leaves = []
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            leaves.append(sha256_bytes(chunk))

    if not leaves:
        return hashlib.sha256(b"").hexdigest()

    # build tree
    while len(leaves) > 1:
        next_level = []
        for i in range(0, len(leaves), 2):
            left = leaves[i]
            right = leaves[i + 1] if i + 1 < len(leaves) else left
            next_level.append(sha256_bytes(left + right))
        leaves = next_level
    return leaves[0].hex()


# endpoint pentru liste & upload
@databases_ns.route('/databases')
class DatabaseListResource(Resource):

    @databases_ns.marshal_list_with(db_model)
    def get(self):
        """ Return all databases """
        return AIDatabase.query.all()


@databases_ns.route('/databases/upload')
class DatabaseUploadResource(Resource):

    @databases_ns.marshal_with(db_model)
    # request should be multipart/form-data: file + name + purpose + model_name (optional) + description (optional)
    @jwt_required()
    def post(self):
        """ Upload a new database file """
        # get authenticated user id from JWT (assumes identity is user id)
        identity = get_jwt_identity()
        if identity is None:
            return {"message": "Unauthorized"}, 401

        # find user
        user = db.session.get(User, identity)
        if not user:
            return {"message": "The user does not exist"}, 404

        # multipart file
        file = request.files.get('file')
        name = request.form.get('name')
        model_name = request.form.get('model_name')
        purpose = request.form.get('purpose')
        description = request.form.get('description')

        if not file or not name or not purpose:
            return {"message": "No file, name or purpose was provided."}, 400

        # ensure upload directory
        dest_dir = os.path.join(UPLOAD_FOLDER, "databases")
        os.makedirs(dest_dir, exist_ok=True)

        # secure filename and save
        filename = secure_filename(file.filename)
        dest_path = os.path.join(dest_dir, filename)
        file.save(dest_path)

        # compute hash (streaming) and size
        data_hash = AIDatabase.calculate_hash(dest_path)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)

        # optional merkle root for chunked verification
        try:
            merkle = merkle_root_from_file(dest_path)
        except Exception:
            merkle = None

        # storage_uri (local file). If you later upload to IPFS/S3, replace this with the proper URI.
        storage_uri = f"file://{dest_path}"

        # create DB entry
        db_entry = AIDatabase(
            name=name,
            model_name=model_name,
            purpose=purpose,
            storage_uri=storage_uri,
            data_hash=data_hash,
            merkle_root=merkle,
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

        # Only uploader or admin should be able to update — basic check
        identity = get_jwt_identity()
        user = db.session.get(User, identity)
        if (not user) or (user.id != db_entry.user_id and not user.is_admin):
            return {"message": "Forbidden"}, 403

        data = request.get_json()
        db_entry.update(**data)

        return db_entry, 200

    @jwt_required()
    def delete(self, database_id):
        """ Delete a database and its file """
        db_entry = AIDatabase.query.get_or_404(database_id)

        identity = get_jwt_identity()
        user = db.session.get(User, identity)
        if (not user) or (user.id != db_entry.user_id and not user.is_admin):
            return {"message": "Forbidden"}, 403

        db_entry.delete()
        return {"message": "Database deleted successfully."}, 200
