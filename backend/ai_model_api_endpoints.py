# backend/ai_model_api_endpoints.py
import os
import re
import json
import subprocess
import time
import hashlib
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
        "model_pda": fields.String(),
        "size_mb": fields.Float(),
        "status": fields.String(),
        "last_error": fields.String(),
        "uploader_id": fields.Integer(required=True),
        "created_at": fields.String(),
    },
)

ALLOWED_EXT = {"pt", "onnx", "bin", "tar", "zip", "pth", "ptm"}


def _extract_last_json(text: str):
    """
    Try to extract the last JSON object/array from `text`.
    Strategy:
      1. Try json.loads(text) directly.
      2. Use regex to find a JSON-like substring at the end.
      3. Try progressively earlier '{' or '[' positions.
    Raises ValueError if nothing parseable is found.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty stdout")

    # 1) direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) regex: find last {...} or [...] near the end (DOTALL)
    m = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])\s*$', text)
    if m:
        cand = m.group(1)
        try:
            return json.loads(cand)
        except Exception:
            # fall through to try other heuristics
            pass

    # 3) fallback: try from last '{' or '[' positions
    positions = []
    pos1 = text.rfind('{')
    pos2 = text.rfind('[')
    if pos1 != -1:
        positions.append(pos1)
    if pos2 != -1:
        positions.append(pos2)
    for start in sorted(positions, reverse=True):
        try:
            substr = text[start:]
            return json.loads(substr)
        except Exception:
            continue

    # give up with diagnostic
    raise ValueError("No valid JSON found in stdout")


def _run_cli_and_parse_json(cmd, timeout=120):
    """
    Run external CLI (list of args) and robustly parse JSON output.
    Returns parsed JSON dict.
    Raises RuntimeError on failure with stdout/stderr included.
    """
    proc = None
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            text=True,
            cwd=os.getcwd(),
            timeout=timeout,
            env=os.environ.copy(),
        )
        out = proc.stdout or ""
        try:
            result = _extract_last_json(out)
            return result
        except Exception as e:
            # include stdout/stderr for debugging
            raise RuntimeError(f"Failed to parse JSON from CLI stdout. stdout={out!r}, stderr={proc.stderr!r}, err={e}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"CLI failed: stdout={e.stdout!r}, stderr={e.stderr!r}")
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"CLI timed out: stdout={e.stdout!r}, stderr={e.stderr!r}")


def call_register_model(model_hash_hex, storage_uri, price_lamports, uploader_wallet_path=None, timeout=120):
    """Call Node.js CLI register_model.js and return JSON result."""
    cli_path = os.environ.get("REGISTER_MODEL_CLI", "blockchain/clients/register_model.js")
    cmd = ["node", cli_path, model_hash_hex, storage_uri, str(price_lamports)]
    if uploader_wallet_path:
        cmd.append(uploader_wallet_path)

    current_app.logger.debug("Calling register CLI: %s", " ".join(cmd))
    result = _run_cli_and_parse_json(cmd, timeout=timeout)
    if not result.get("success"):
        raise RuntimeError(f"CLI returned success=false: {result}")
    return result


def call_rent_model(model_hash_hex, renter_wallet_path=None, timeout=120):
    """Call Node.js CLI rent_model.js and return txid."""
    cli_path = os.environ.get("RENT_MODEL_CLI", "blockchain/clients/rent_model.js")
    cmd = ["node", cli_path, model_hash_hex]
    if renter_wallet_path:
        cmd.append(renter_wallet_path)

    current_app.logger.debug("Calling rent CLI: %s", " ".join(cmd))
    result = _run_cli_and_parse_json(cmd, timeout=timeout)
    if not result.get("success"):
        raise RuntimeError(f"Rent CLI returned success=false: {result}")
    return result.get("txid")


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
        identity = get_jwt_identity()
        uploader = db.session.get(User, identity)
        if not uploader:
            return {"message": "User not found"}, 404

        file = request.files.get("file")
        name = request.form.get("name")
        description = request.form.get("description")
        price_lamports = int(request.form.get("price_lamports") or 0)

        if not file or not name:
            return {"message": "Missing file or name"}, 400

        dest_dir = os.path.join(UPLOAD_FOLDER, "models")
        os.makedirs(dest_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        dest_path = os.path.join(dest_dir, filename)
        file.save(dest_path)

        ext = filename.rsplit(".", 1)[-1].lower()

        try:
            if ext in {"pt", "pth", "ptm"}:
                import torch
                obj = torch.load(dest_path, map_location="cpu")
                model_hash = canonical_state_dict_hash(obj)
            else:
                model_hash = file_sha256_stream(dest_path)
        except Exception as e:
            current_app.logger.warning(
                "canonical hash failed: %s; falling back to streaming sha256", e
            )
            model_hash = file_sha256_stream(dest_path)

        # generate a unique hash for on-chain PDA (avoid duplicates)
        salt = str(time.time_ns()).encode("utf-8")
        try:
            hash_onchain = hashlib.sha256(bytes.fromhex(model_hash) + salt).hexdigest()
        except Exception:
            # fallback: hash of model_hash + salt string
            hash_onchain = hashlib.sha256(model_hash.encode("utf-8") + salt).hexdigest()

        try:
            merkle = merkle_root_from_file(dest_path)
        except Exception:
            merkle = None

        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        storage_uri = f"file://{dest_path}"

        model = AIModel(
            uploader_id=uploader.id,
            name=name,
            description=description,
            model_hash=model_hash,
            merkle_root=merkle,
            storage_uri=storage_uri,
            price_lamports=price_lamports,
            size_mb=size_mb,
            status="pending",
        )
        model.save()

        # On-chain registration using hash_onchain
        uploader_wallet_path = request.form.get("uploader_wallet_path")
        try:
            result = call_register_model(hash_onchain, storage_uri, price_lamports, uploader_wallet_path)
            model.onchain_tx = result.get("txid")
            model.model_pda = result.get("model_pda")
            model.status = "registered"
            model.last_error = None
        except Exception as e:
            # log full exception for debugging, but store a cropped version in DB
            current_app.logger.exception("Onchain registration failed")
            model.status = "failed"
            model.last_error = str(e)[:1000]  # crop error string

        db.session.commit()
        return model, 201


@models_ns.route("/models/<int:model_id>")
class ModelResource(Resource):
    @models_ns.marshal_with(model_schema)
    def get(self, model_id):
        return AIModel.query.get_or_404(model_id)

    @models_ns.marshal_with(model_schema)
    @models_ns.expect(model_schema)
    @jwt_required()
    def put(self, model_id):
        model = AIModel.query.get_or_404(model_id)
        identity = get_jwt_identity()
        user = db.session.get(User, identity)
        if (not user) or (user.id != model.uploader_id and not user.is_admin):
            return {"message": "Forbidden"}, 403

        data = request.get_json()
        immutable = {"model_hash", "merkle_root", "storage_uri", "uploader_id", "onchain_tx", "size_mb"}
        for k in immutable:
            data.pop(k, None)
        model.update(**data)
        return model, 200

    @jwt_required()
    def delete(self, model_id):
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
        model = AIModel.query.get_or_404(model_id)
        identity = get_jwt_identity()
        renter = db.session.get(User, identity)
        if not renter:
            return {"message": "Renter not found"}, 404

        renter_wallet_path = request.form.get("renter_wallet_path")
        try:
            txid = call_rent_model(model.model_hash, renter_wallet_path)
        except Exception as e:
            current_app.logger.exception("On-chain rent failed")
            return {"message": "On-chain rent failed", "error": str(e)}, 500

        return {"message": "Rented", "txid": txid}, 200
