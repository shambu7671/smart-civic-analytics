"""
Firebase Storage Integration Service
====================================
Uploads and manages report images in Firebase Cloud Storage.
This enables persistent cloud image storage when running on serverless
platforms like Vercel where the local filesystem is ephemeral and read-only.
"""
import os
import json
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

_firebase_app = None


def get_firebase_app():
    """Initializes or returns the cached Firebase Admin app instance."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized in another thread/process
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass

        bucket_name = current_app.config.get("FIREBASE_STORAGE_BUCKET") or os.getenv("FIREBASE_STORAGE_BUCKET")
        cred_json_str = current_app.config.get("FIREBASE_CREDENTIALS_JSON") or os.getenv("FIREBASE_CREDENTIALS_JSON")
        cred_file_path = current_app.config.get("FIREBASE_CREDENTIALS_PATH") or os.getenv("FIREBASE_CREDENTIALS_PATH")

        cred = None
        if cred_json_str:
            try:
                cred_dict = json.loads(cred_json_str)
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                logger.warning(f"Could not parse FIREBASE_CREDENTIALS_JSON: {e}")

        if not cred and cred_file_path and os.path.exists(cred_file_path):
            try:
                cred = credentials.Certificate(cred_file_path)
            except Exception as e:
                logger.warning(f"Could not load FIREBASE_CREDENTIALS_PATH: {e}")

        if not cred:
            # Fall back to Google Application Default Credentials
            try:
                cred = credentials.ApplicationDefault()
            except Exception:
                cred = None

        if cred:
            options = {"storageBucket": bucket_name} if bucket_name else None
            _firebase_app = firebase_admin.initialize_app(cred, options)
            logger.info("Firebase Admin initialized")
            return _firebase_app
        else:
            return None

    except Exception as exc:
        logger.warning(f"Firebase Admin initialization failed: {exc}")
        return None


def is_firebase_enabled() -> bool:
    """Returns True if Firebase Storage is configured and ready."""
    return bool(current_app.config.get("FIREBASE_STORAGE_BUCKET") and get_firebase_app())


def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase Authentication ID token and return its trusted claims."""
    app = get_firebase_app()
    if not app:
        raise RuntimeError("Firebase Admin is not configured.")
    import firebase_admin.auth
    return firebase_admin.auth.verify_id_token(id_token, app=app, check_revoked=True)


def upload_to_firebase(local_path: str, destination_blob_name: str) -> str:
    """
    Uploads a local file to private Firebase Storage.
    Returns a gs:// path that the server can read without exposing the object.
    """
    app = get_firebase_app()
    if not app:
        return ""

    try:
        from firebase_admin import storage
        bucket = storage.bucket(app=app)
        blob = bucket.blob(destination_blob_name)

        # Infer content type
        ext = Path(local_path).suffix.lower()
        content_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "application/octet-stream"

        blob.upload_from_filename(local_path, content_type=content_type)
        return f"gs://{bucket.name}/{blob.name}"

    except Exception as exc:
        logger.error(f"Failed to upload {local_path} to Firebase: {exc}")
        return ""


def download_from_firebase(blob_name: str, local_destination: str) -> bool:
    """Downloads a blob from Firebase Storage to local disk (e.g. /tmp)."""
    app = get_firebase_app()
    if not app:
        return False

    try:
        from firebase_admin import storage
        bucket = storage.bucket(app=app)
        blob = bucket.blob(blob_name)
        Path(local_destination).parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(local_destination)
        return True
    except Exception as exc:
        logger.error(f"Failed to download {blob_name} from Firebase: {exc}")
        return False


def download_image_bytes(blob_name: str, max_bytes: int) -> bytes:
    """Read a bounded image object from the configured private Firebase bucket."""
    app = get_firebase_app()
    if not app:
        raise RuntimeError("Firebase Admin is not configured.")
    from firebase_admin import storage
    blob = storage.bucket(app=app).blob(blob_name)
    blob.reload()
    if blob.size is None or blob.size > max_bytes:
        raise ValueError("Stored image exceeds the configured size limit.")
    return blob.download_as_bytes()
