import os
import secrets
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

if os.getenv("VERCEL") and not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY must be set for a Vercel deployment.")
if os.getenv("VERCEL") and not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL must point to the Supabase PostgreSQL session pooler.")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep a small reusable pool for serverless invocations. Supabase session
    # pooler connection strings are recommended for production deployments.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 2,
        "max_overflow": 0,
    }
    # For Vercel serverless environments, writable directory is /tmp
    _raw_upload = os.getenv("UPLOAD_FOLDER", "/tmp/uploads" if os.getenv("VERCEL") else "uploads")
    UPLOAD_FOLDER = _raw_upload if os.path.isabs(_raw_upload) else str(BASE_DIR / _raw_upload)
    MAX_CONTENT_LENGTH = int(float(os.getenv("MAX_UPLOAD_SIZE_MB", "8")) * 1024 * 1024)
    AI_MODE = os.getenv("AI_MODE", "demo").lower()
    AI_MODEL_PATH = str(BASE_DIR / os.getenv("AI_MODEL_PATH", "ai/models/best.pt"))
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.55"))
    DUPLICATE_RADIUS_METERS = float(os.getenv("DUPLICATE_RADIUS_METERS", "100"))
    DUPLICATE_AUTO_LINK_THRESHOLD = float(os.getenv("DUPLICATE_AUTO_LINK_THRESHOLD", "0.82"))
    DUPLICATE_CANDIDATE_THRESHOLD = float(os.getenv("DUPLICATE_CANDIDATE_THRESHOLD", "0.45"))
    DUPLICATE_LOCATION_WEIGHT = float(os.getenv("DUPLICATE_LOCATION_WEIGHT", "0.30"))
    DUPLICATE_CATEGORY_WEIGHT = float(os.getenv("DUPLICATE_CATEGORY_WEIGHT", "0.20"))
    DUPLICATE_IMAGE_WEIGHT = float(os.getenv("DUPLICATE_IMAGE_WEIGHT", "0.30"))
    DUPLICATE_TEXT_WEIGHT = float(os.getenv("DUPLICATE_TEXT_WEIGHT", "0.20"))
    IMAGE_SIMILARITY_THRESHOLD = float(os.getenv("IMAGE_SIMILARITY_THRESHOLD", "0.65"))
    TEXT_SIMILARITY_THRESHOLD = float(os.getenv("TEXT_SIMILARITY_THRESHOLD", "0.35"))
    DBSCAN_EPS_METERS = float(os.getenv("DBSCAN_EPS_METERS", "80"))
    DBSCAN_MIN_SAMPLES = int(os.getenv("DBSCAN_MIN_SAMPLES", "2"))
    SEVERITY_WEIGHT = float(os.getenv("SEVERITY_WEIGHT", "0.35"))
    REPORT_WEIGHT = float(os.getenv("REPORT_WEIGHT", "0.25"))
    AGE_WEIGHT = float(os.getenv("AGE_WEIGHT", "0.20"))
    LOCATION_WEIGHT = float(os.getenv("LOCATION_WEIGHT", "0.20"))
    HIGH_PRIORITY_THRESHOLD = float(os.getenv("HIGH_PRIORITY_THRESHOLD", "70"))
    MEDIUM_PRIORITY_THRESHOLD = float(os.getenv("MEDIUM_PRIORITY_THRESHOLD", "45"))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    JSON_SORT_KEYS = False

    # ── Firebase Storage (optional for cloud uploads) ─────────────────────────
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    # ─────────────────────────────────────────────────────────────────────────
    # ── Geotag / EXIF GPS verification ───────────────────────────────────────
    # Maximum allowed distance (metres) between EXIF GPS and submitted coordinates
    # for a report to receive VERIFIED status.
    GEOTAG_MAX_DISTANCE_METERS = float(os.getenv("GEOTAG_MAX_DISTANCE_METERS", "200"))
    # "warn"   → mismatch is logged and stored but submission is still accepted.
    # "strict" → MISMATCH result blocks the submission with a 400 error.
    GEOTAG_ENFORCEMENT_MODE = os.getenv("GEOTAG_ENFORCEMENT_MODE", "warn").lower()
    # Vercel instances must not run schema DDL or seed writes during import.
    SKIP_DB_INIT = os.getenv("SKIP_DB_INIT", "true" if os.getenv("VERCEL") else "false").lower() == "true"
    # ────────────────────────────────────────────────────────────────────────

