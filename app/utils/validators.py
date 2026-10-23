import mimetypes
from pathlib import Path
from flask import current_app
from werkzeug.datastructures import FileStorage

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_MIME = {"image/jpeg", "image/png"}


def validate_image(file: FileStorage):
    if not file or not file.filename:
        return False, "An image is required."
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only JPG, JPEG and PNG images are allowed."
    guessed = file.mimetype or mimetypes.guess_type(file.filename)[0]
    if guessed not in ALLOWED_MIME:
        return False, "Invalid image MIME type."
    return True, None


def valid_coordinates(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_password(password: str):
    if not password or len(password) < 8:
        return False, "Password must contain at least 8 characters."
    return True, None
