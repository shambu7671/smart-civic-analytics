from datetime import datetime, timezone
from app import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    # Firebase Authentication owns credentials; this UID links the verified
    # Firebase identity to the application's relational user record.
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    mobile = db.Column(db.String(30), nullable=False)
    # Kept nullable for existing accounts migrated to Firebase Auth.
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="CITIZEN")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
