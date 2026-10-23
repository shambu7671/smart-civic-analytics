from app import db


class IssueCategory(db.Model):
    __tablename__ = "issue_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text)
