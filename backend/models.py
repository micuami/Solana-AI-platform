from exts import db
import hashlib
import os


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.Text(), nullable=False)

    # relatie: un user poate avea mai multe baze de date
    databases = db.relationship('AIDatabase', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def save(self):
        db.session.add(self)
        db.session.commit()


class AIDatabase(db.Model):
    __tablename__ = 'ai_databases'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)            # nume baza de date
    model_name = db.Column(db.String(100), nullable=True)       # model AI asociat
    purpose = db.Column(db.String(50), nullable=False)          # training, testing, inference
    file_path = db.Column(db.String(200), nullable=False)       # locatia fisierului
    file_hash = db.Column(db.String(64), nullable=False)        # hash pentru integritate
    size_mb = db.Column(db.Float, nullable=False)               # dimensiunea fisierului
    description = db.Column(db.String(200))                     # descriere (optional)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # foreign key spre user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<AIDatabase {self.name}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        db.session.delete(self)
        db.session.commit()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()

    @staticmethod
    def calculate_hash(file_path):
        """ Generate SHA-256 hash for a file """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
