# backend/ai_model_api_endpoints.py
import os
import json
import subprocess
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request, current_app
from werkzeug.utils import secure_filename

from backend.externals import db
from backend.models import AIModel, User
from backend.constants import UPLOAD_FOLDER
from backend.utils.hash_utils import (
    canonical_state_dict_hash,
    file_sha256_stream,
    merkle_root_from_file,
)

models_ns = Namespace("models", description="A namespace for AI Models")

model_schema = models_ns.model(
    "AIModel",
    {
        "id": fields.Integer(readOnly=True),
        "name": fields.String(required=True),
        "description": fields.String(),
        "model_hash": fields.String(),
        "merkle_root": fields.String(),
        "storage_uri": fields.String(),
        "price_lamports": fields.Integer(),
        "onchain_tx": fields.String(),
        "size_mb": fields.Float(),
        "uploader_id": fields.Integer(required=True),
        "created_at": fields.String(),
    },
)

ALLOWED_EXT = {"pt", "onnx", "bin", "tar", "zip", "pth", "ptm"}

# helper: call external JS/TS CLI that registers model on-chain via Anchor
def register_model_onchain_cli(model_hash_hex, storage_uri, price_lamports, uploader_wallet_path=None):
    """
    Calls an external script (node/ts) that performs the Anchor RPC create_model.
    Expected to return JSON on stdout: {"txid":"..."} on success.
    uploader_wallet_path: optional path to keypair used to sign the tx.
    """
    cli_path = os.environ.get("REGISTER_MODEL_CLI", "blockchain/clients/register_model.js")
    cmd = ["node", cli_path, model_hash_hex, storage_uri, str(price_lamports)]
    if uploader_wallet_path:
        cmd.append(uploader_wallet_path)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            text=True,
            cwd=os.getcwd(),
        )
        out = proc.stdout.strip()
        try:
            parsed = json.loads(out)
            return parsed.get("txid")
        except Exception:
            current_app.logger.warning("register_model_onchain_cli: couldn't parse JSON from stdout: %s", out)
            return out or None
    except subprocess.CalledProcessError as e:
        current_app.logger.error("Onchain registration failed: %s %s", e.stdout, e.stderr)
        return None


# helper: call external CLI to rent model on-chain (performe rent RPC)
def rent_model_onchain_cli(model_hash_hex, renter_wallet_path=None):
    """
    Calls external script to invoke rent_model in Anchor program.
    Expected JSON stdout: {"txid":"..."}.
    """
    cli_path = os.environ.get("RENT_MODEL_CLI", "blockchain/clients/rent_model.js")
    cmd = ["node", cli_path, model_hash_hex]
    if renter_wallet_path:
        cmd.append(renter_wallet_path)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, check=True, text=True, cwd=os.getcwd()
        )
        out = proc.stdout.strip()
        try:
            parsed = json.loads(out)
            return parsed.get("txid")
        except Exception:
            current_app.logger.warning("rent_model_onchain_cli: couldn't parse JSON from stdout: %s", out)
            return out or None
    except subprocess.CalledProcessError as e:
        current_app.logger.error("Rent onchain failed: %s %s", e.stdout, e.stderr)
        return None


@models_ns.route("/models")
class ModelListResource(Resource):
    @models_ns.marshal_list_with(model_schema)
    def get(self):
        """Return all models"""
        return AIModel.query.all()


@models_ns.route("/models/upload")
class ModelUploadResource(Resource):
    @models_ns.marshal_with(model_schema)
    @jwt_required()
    def post(self):
        """
        Upload a new AI model.
        multipart/form-data: file + name + description (optional) + price_lamports (optional)
        """
        identity = get_jwt_identity()
        if identity is None:
            return {"message": "Unauthorized"}, 401
        uploader = db.session.get(User, identity)
        if not uploader:
            return {"message": "User not found"}, 404

        file = request.files.get("file")
        name = request.form.get("name")
        description = request.form.get("description")
        price_lamports = int(request.form.get("price_lamports") or 0)

        if not file or not name:
            return {"message": "Missing file or name"}, 400

        # save file locally first
        dest_dir = os.path.join(UPLOAD_FOLDER, "models")
        os.makedirs(dest_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        dest_path = os.path.join(dest_dir, filename)
        file.save(dest_path)

        # compute hash: canonical for PyTorch (.pt/.pth) else streaming sha256
        ext = filename.rsplit(".", 1)[-1].lower()
        try:
            if ext in {"pt", "pth", "ptm"}:
                # load torch model/state_dict and compute canonical hash
                import torch

                obj = torch.load(dest_path, map_location="cpu")
                model_hash = canonical_state_dict_hash(obj)
            else:
                model_hash = file_sha256_stream(dest_path)
        except Exception as e:
            # fallback to streaming if canonical fails
            current_app.logger.warning("canonical hash failed: %s; falling back to streaming sha256", e)
            model_hash = file_sha256_stream(dest_path)

        # merkle root (optional)
        try:
            merkle = merkle_root_from_file(dest_path)
        except Exception:
            merkle = None

        size_mb = os.path.getsize(dest_path) / (1024 * 1024)

        storage_uri = f"file://{dest_path}"  # replace with IPFS/S3 upload when available

        # create DB entry
        model = AIModel(
            uploader_id=uploader.id,
            name=name,
            description=description,
            model_hash=model_hash,
            merkle_root=merkle,
            storage_uri=storage_uri,
            price_lamports=price_lamports,
            size_mb=size_mb,
        )
        model.save()

        # Register on-chain - try to use uploader's wallet path if provided in form (optional)
        uploader_wallet_path = request.form.get("uploader_wallet_path")
        txid = register_model_onchain_cli(model_hash, storage_uri, price_lamports, uploader_wallet_path)
        model.onchain_tx = txid
        db.session.commit()

        return model, 201


@models_ns.route("/models/<int:model_id>")
class ModelResource(Resource):
    @models_ns.marshal_with(model_schema)
    def get(self, model_id):
        """Get a single model"""
        return AIModel.query.get_or_404(model_id)

    @models_ns.marshal_with(model_schema)
    @models_ns.expect(model_schema)
    @jwt_required()
    def put(self, model_id):
        """Update model metadata (not model file)."""
        model = AIModel.query.get_or_404(model_id)
        identity = get_jwt_identity()
        user = db.session.get(User, identity)
        if (not user) or (user.id != model.uploader_id and not user.is_admin):
            return {"message": "Forbidden"}, 403

        data = request.get_json()
        # Prevent changing immutable fields like model_hash via this endpoint
        immutable = {"model_hash", "merkle_root", "storage_uri", "uploader_id", "onchain_tx", "size_mb"}
        for k in immutable:
            if k in data:
                data.pop(k)
        model.update(**data)
        return model, 200

    @jwt_required()
    def delete(self, model_id):
        """Delete a model and its local file (if any)."""
        model = AIModel.query.get_or_404(model_id)
        identity = get_jwt_identity()
        user = db.session.get(User, identity)
        if (not user) or (user.id != model.uploader_id and not user.is_admin):
            return {"message": "Forbidden"}, 403

        model.delete()
        return {"message": "Model deleted."}, 200


@models_ns.route("/models/<int:model_id>/rent")
class ModelRentResource(Resource):
    @jwt_required()
    def post(self, model_id):
        """
        Rent a model: triggers on-chain rent transaction.
        The renter should provide optional renter_wallet_path in form if server should use it to sign.
        (Prefer client-side signing in production.)
        """
        model = AIModel.query.get_or_404(model_id)
        identity = get_jwt_identity()
        renter = db.session.get(User, identity)
        if not renter:
            return {"message": "Renter not found"}, 404

        # in production prefer renter signs transaction client-side; here we allow CLI path optional
        renter_wallet_path = request.form.get("renter_wallet_path")
        txid = rent_model_onchain_cli(model.model_hash, renter_wallet_path)
        if not txid:
            return {"message": "On-chain rent failed"}, 500

        return {"message": "Rented", "txid": txid}, 200
