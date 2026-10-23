from datetime import datetime, timezone
from app import db
from geoalchemy2 import Geography


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("issue_categories.id"), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location_geometry = db.Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    submission_status = db.Column(db.String(30), nullable=False, default="SUBMITTED", index=True)
    self_reported_severity = db.Column(db.Integer, nullable=False, default=3)
    original_text = db.Column(db.Text)
    translated_text = db.Column(db.Text)
    detected_language = db.Column(db.String(10), default="en")
    selected_language = db.Column(db.String(10), default="en")
    recommended_department = db.Column(db.String(100))
    suggested_action = db.Column(db.Text)
    # ── Geotag / EXIF GPS verification ──────────────────────────────────────
    # Possible values: VERIFIED | MISMATCH | NO_EXIF_GPS | EXTRACTION_ERROR | PENDING
    geotag_status = db.Column(db.String(30), nullable=False, default="PENDING", index=True)
    geotag_lat = db.Column(db.Float)           # Latitude extracted from EXIF
    geotag_lon = db.Column(db.Float)           # Longitude extracted from EXIF
    geotag_altitude = db.Column(db.Float)      # Altitude in metres from EXIF (optional)
    geotag_distance_m = db.Column(db.Float)    # Haversine distance: EXIF ↔ submitted (metres)
    geotag_message = db.Column(db.Text)        # Human-readable verification result
    # ────────────────────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref="reports")
    category = db.relationship("IssueCategory")
