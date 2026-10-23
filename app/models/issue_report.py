from datetime import datetime, timezone
from app import db


class IssueReport(db.Model):
    __tablename__ = "issue_reports"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    linked_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    link_method = db.Column(db.String(30), nullable=False)

    issue = db.relationship("Issue", backref=db.backref("issue_reports", cascade="all, delete-orphan"))
    report = db.relationship("Report")
