from datetime import datetime, timezone
from app import db


class AIDetection(db.Model):
    __tablename__ = "ai_detections"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(100), nullable=False)
    detected_category = db.Column(db.String(80))
    confidence_score = db.Column(db.Float)
    bounding_box = db.Column(db.JSON)
    status = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processing_time_ms = db.Column(db.Float)

    report = db.relationship("Report", backref=db.backref("ai_detection", uselist=False))
