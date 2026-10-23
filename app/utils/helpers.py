from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import unquote, urlparse


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat() if dt else None


def to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def stored_image_filename(path):
    """Return a safe basename for local, gs://, or legacy Firebase URL paths."""
    value = str(path)
    parsed = urlparse(value)
    value = unquote(parsed.path) if parsed.scheme in {"http", "https", "gs"} else value
    return value.replace("\\", "/").rsplit("/", 1)[-1].split("?", 1)[0]
