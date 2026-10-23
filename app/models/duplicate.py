from datetime import datetime, timezone
from app import db


class DuplicateCandidate(db.Model):
    __tablename__ = "duplicate_candidates"
    id = db.Column(db.Integer, primary_key=True)
    new_report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    existing_report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    distance_meters = db.Column(db.Float, nullable=False)
    category_similarity = db.Column(db.Float, nullable=False)
    image_similarity = db.Column(db.Float, nullable=False)
    text_similarity = db.Column(db.Float, nullable=False)
    overall_similarity = db.Column(db.Float, nullable=False, index=True)
    decision = db.Column(db.String(30), nullable=False, default="PENDING", index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    new_report = db.relationship("Report", foreign_keys=[new_report_id])
    existing_report = db.relationship("Report", foreign_keys=[existing_report_id])
    reviewer = db.relationship("User")
