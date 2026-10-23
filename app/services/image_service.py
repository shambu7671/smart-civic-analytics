import hashlib
import os
import uuid
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from pathlib import Path
import cv2
import numpy as np
from flask import current_app
from werkzeug.utils import secure_filename


def save_image(file_storage):
    original = secure_filename(file_storage.filename)
    ext = Path(original).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    file_storage.save(path)
    # Decode once to ensure the uploaded content is actually readable as an image.
    image = cv2.imread(str(path))
    if image is None:
        path.unlink(missing_ok=True)
        raise ValueError("Uploaded content is not a readable image.")

    # ── Upload to Firebase Storage if configured ──────────────────────────────
    vercel = bool(os.getenv("VERCEL"))
    try:
        from app.services.firebase_service import is_firebase_enabled, upload_to_firebase
        if is_firebase_enabled():
            firebase_path = upload_to_firebase(str(path), f"uploads/{filename}")
            if firebase_path:
                # Keep the local copy available for EXIF extraction in this request.
                return firebase_path, filename, str(path)
        if vercel:
            raise ValueError("Firebase Storage must be configured for persistent report images on Vercel.")
    except ValueError:
        path.unlink(missing_ok=True)
        raise
    except Exception:
        if vercel:
            path.unlink(missing_ok=True)
            raise ValueError("Could not save the report image to Firebase Storage. Please try again.")

    return str(path), filename, str(path)


def _read_image(path, flags):
    """Read a local image or a Firebase Storage URL without allowing arbitrary hosts."""
    value = str(path)
    if value.startswith("gs://"):
        try:
            bucket_and_blob = value[5:]
            bucket_name, blob_name = bucket_and_blob.split("/", 1)
            if bucket_name != current_app.config.get("FIREBASE_STORAGE_BUCKET"):
                return None
            from app.services.firebase_service import download_image_bytes
            data = download_image_bytes(blob_name, int(current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)))
            return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)
        except Exception:
            return None
    if not value.startswith(("https://", "http://")):
        return cv2.imread(value, flags)
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"storage.googleapis.com", "firebasestorage.googleapis.com"}:
        return None
    max_bytes = int(current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024))
    try:
        request = Request(value, headers={"User-Agent": "SmartCivic/1.0"})
        with urlopen(request, timeout=8) as response:
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)
    except Exception:
        return None


def perceptual_similarity(path_a, path_b):
    a = _read_image(path_a, cv2.IMREAD_GRAYSCALE)
    b = _read_image(path_b, cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        return 0.0
    a = cv2.resize(a, (32, 32))
    b = cv2.resize(b, (32, 32))
    a = cv2.GaussianBlur(a, (5, 5), 0)
    b = cv2.GaussianBlur(b, (5, 5), 0)
    a = a.astype(np.float32) / 255.0
    b = b.astype(np.float32) / 255.0
    mse = float(np.mean((a - b) ** 2))
    return max(0.0, min(1.0, 1.0 - mse * 4.0))


def file_fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
