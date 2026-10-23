from datetime import datetime, timezone
from app import db
from geoalchemy2 import Geography


class Issue(db.Model):
    __tablename__ = "issues"
    id = db.Column(db.Integer, primary_key=True)
    issue_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("issue_categories.id"), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_geometry = db.Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    severity = db.Column(db.Integer, nullable=False, default=3)
    severity_source = db.Column(db.String(20), nullable=False, default="CITIZEN")
    report_count = db.Column(db.Integer, nullable=False, default=1)
    age_score = db.Column(db.Float, nullable=False, default=0)
    location_importance = db.Column(db.Integer, nullable=False, default=1)
    priority_score = db.Column(db.Float, nullable=False, default=0)
    priority_level = db.Column(db.String(10), nullable=False, default="LOW", index=True)
    status = db.Column(db.String(30), nullable=False, default="REPORTED", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True))

    category = db.relationship("IssueCategory")
