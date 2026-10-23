"""Private report-image storage backed by Supabase Storage's REST API."""
import logging
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import current_app

logger = logging.getLogger(__name__)


def _settings():
    base_url = (current_app.config.get("SUPABASE_URL") or "").rstrip("/")
    service_key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY")
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET") or "report-images"
    if not base_url or not service_key:
        raise RuntimeError("Supabase Storage is not configured.")
    return base_url, service_key, bucket


def is_supabase_storage_enabled():
    return bool(
        current_app.config.get("SUPABASE_URL")
        and current_app.config.get("SUPABASE_SERVICE_ROLE_KEY")
        and current_app.config.get("SUPABASE_STORAGE_BUCKET", "report-images")
    )


def _object_url(base_url, bucket, object_key):
    if not object_key or object_key.startswith("/") or ".." in object_key.split("/"):
        raise ValueError("Invalid Supabase Storage object path.")
    encoded_key = "/".join(quote(part, safe="") for part in object_key.split("/"))
    return f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{encoded_key}"


def upload_image(local_path: str, object_key: str) -> str:
    """Upload a private image and return its stable database reference."""
    base_url, service_key, bucket = _settings()
    ext = Path(local_path).suffix.lower()
    content_type = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png"
    with open(local_path, "rb") as source:
        payload = source.read(int(current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)) + 1)
    if len(payload) > int(current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)):
        raise ValueError("Uploaded image exceeds the configured size limit.")
    request = Request(
        _object_url(base_url, bucket, object_key),
        data=payload,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": content_type,
            "x-upsert": "false",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(f"Supabase Storage upload returned HTTP {response.status}.")
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Supabase Storage upload failed: %s", getattr(exc, "code", type(exc).__name__))
        raise RuntimeError("Could not save the report photo to Supabase Storage.") from exc
    return f"supabase://{bucket}/{object_key}"


def download_image_bytes(object_key: str, max_bytes: int, bucket: str = None) -> bytes:
    """Download a bounded object from the private report-images bucket."""
    base_url, service_key, configured_bucket = _settings()
    bucket = bucket or configured_bucket
    request = Request(
        _object_url(base_url, bucket, object_key),
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = response.read(max_bytes + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Supabase Storage download failed: %s", getattr(exc, "code", type(exc).__name__))
        raise RuntimeError("Could not read the report photo from Supabase Storage.") from exc
    if len(payload) > max_bytes:
        raise ValueError("Stored image exceeds the configured size limit.")
    return payload


def delete_image(object_key: str, bucket: str = None):
    """Delete an uploaded object when a report cannot be saved."""
    base_url, service_key, configured_bucket = _settings()
    request = Request(
        _object_url(base_url, bucket or configured_bucket, object_key),
        method="DELETE",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            if response.status not in {200, 204}:
                raise RuntimeError(f"Supabase Storage delete returned HTTP {response.status}.")
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Supabase Storage cleanup failed: %s", getattr(exc, "code", type(exc).__name__))


def parse_storage_reference(reference: str):
    """Return the bucket and object key from a supabase://bucket/key reference."""
    if not str(reference).startswith("supabase://"):
        return None
    value = str(reference)[len("supabase://"):]
    bucket, separator, object_key = value.partition("/")
    if not separator or not bucket or not object_key:
        raise ValueError("Invalid Supabase Storage image reference.")
    return bucket, object_key
