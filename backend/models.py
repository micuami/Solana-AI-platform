import hashlib
import os
from datetime import datetime
from backend.externals import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # relatii: un user poate avea multiple baze de date si multiple modele
    databases = db.relationship('AIDatabase', backref='uploader', lazy='dynamic', cascade="all, delete-orphan")
    models = db.relationship('AIModel', backref='uploader', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def save(self):
        db.session.add(self)
        db.session.commit()


class AIDatabase(db.Model):
    __tablename__ = 'ai_databases'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)            # nume baza de date
    model_name = db.Column(db.String(100), nullable=True)       # model AI asociat (optional)
    purpose = db.Column(db.String(50), nullable=False)          # training, testing, inference
    storage_uri = db.Column(db.String(1024), nullable=False)    # uri: file://, ipfs://, s3:// etc.
    data_hash = db.Column(db.String(64), nullable=False, index=True)  # hex sha256
    merkle_root = db.Column(db.String(64), nullable=True)       # optional hex merkle root
    size_mb = db.Column(db.Float, nullable=False)               # dimensiunea fisierului în MB
    description = db.Column(db.String())                        # descriere (optional)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # foreign key spre user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<AIDatabase {self.name}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        # sterge fisierul local doar daca storage_uri indica local file path
        try:
            if self.storage_uri and self.storage_uri.startswith("file://"):
                path = self.storage_uri[len("file://"):]
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            # nu vrem sa aruncam exceptii din delete DB; loghează în aplicatie
            pass
        db.session.delete(self)
        db.session.commit()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()

    @staticmethod
    def calculate_hash(file_path, chunk_size=4*1024*1024):
        """ Generate SHA-256 hash for a file (streaming, memory-safe) """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


class AIModel(db.Model):
    __tablename__ = 'ai_models'

    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    model_hash = db.Column(db.String(64), nullable=False, index=True)    # hex sha256 (canonical)
    merkle_root = db.Column(db.String(64), nullable=True)               # optional hex merkle root
    storage_uri = db.Column(db.String(1024), nullable=False)            # ipfs://, s3://, file://...
    price_lamports = db.Column(db.BigInteger, nullable=True)            # pret (dacă folosești monetizare)
    onchain_tx = db.Column(db.String(128), nullable=True)               # txid on-chain daca s-a facut notarizarea
    size_mb = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AIModel {self.name}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        # similar delete behavior ca la AIDatabase
        try:
            if self.storage_uri and self.storage_uri.startswith("file://"):
                path = self.storage_uri[len("file://"):]
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        db.session.delete(self)
        db.session.commit()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()

    @staticmethod
    def calculate_file_hash(file_path, chunk_size=4*1024*1024):
        """ streaming sha256 for large model files """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
