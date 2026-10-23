from datetime import datetime, timezone
from app import db


class IssueStatusHistory(db.Model):
    __tablename__ = "issue_status_history"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = db.Column(db.String(30))
    new_status = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    remarks = db.Column(db.Text)
    changed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    issue = db.relationship("Issue", backref=db.backref("status_history", cascade="all, delete-orphan"))
    user = db.relationship("User")


class IssueAssignment(db.Model):
    __tablename__ = "issue_assignments"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    remarks = db.Column(db.Text)
    assigned_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True))

    issue = db.relationship("Issue", backref=db.backref("assignments", cascade="all, delete-orphan"))


class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(120), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
