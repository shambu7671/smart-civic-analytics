"""
Geotag Verification Service
============================
Extracts GPS EXIF metadata from uploaded JPEG/PNG images using Pillow
and compares the embedded coordinates against the citizen-submitted GPS
coordinates.

Result statuses
---------------
VERIFIED      — EXIF GPS found and is within GEOTAG_MAX_DISTANCE_METERS of submitted coords.
MISMATCH      — EXIF GPS found but location differs by more than the allowed threshold.
NO_EXIF_GPS   — Image has no GPS EXIF (e.g. screenshot, camera without GPS, stripped metadata).
EXTRACTION_ERROR — Could not read EXIF data; treated as advisory warning, not a hard block.
"""

import math
from pathlib import Path
from flask import current_app

try:
    from PIL import Image, ExifTags
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# EXIF GPS extraction
# ──────────────────────────────────────────────────────────────────────────────

def _dms_to_decimal(dms_values, hemisphere: str) -> float:
    """Convert DMS (degrees, minutes, seconds) tuple to a signed decimal float."""
    degrees = float(dms_values[0])
    minutes = float(dms_values[1])
    seconds = float(dms_values[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if hemisphere in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_exif_gps(image_path: str) -> dict:
    """
    Read GPS tags from JPEG/PNG EXIF.

    Returns a dict with keys:
      found  : bool
      lat    : float or None
      lon    : float or None
      altitude: float or None
      error  : str or None
    """
    if not _PIL_AVAILABLE:
        return {"found": False, "lat": None, "lon": None, "altitude": None,
                "error": "Pillow not installed."}

    try:
        img = Image.open(image_path)
        exif_data = img._getexif()      # Returns None for PNG / no EXIF
        if not exif_data:
            return {"found": False, "lat": None, "lon": None, "altitude": None, "error": None}

        # Build tag-name → value mapping
        tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif_data.items()}
        gps_raw = tag_map.get("GPSInfo")
        if not gps_raw:
            return {"found": False, "lat": None, "lon": None, "altitude": None, "error": None}

        # GPSInfo sub-tags
        gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

        lat_dms = gps_tags.get("GPSLatitude")
        lat_ref = gps_tags.get("GPSLatitudeRef", "N")
        lon_dms = gps_tags.get("GPSLongitude")
        lon_ref = gps_tags.get("GPSLongitudeRef", "E")

        if lat_dms is None or lon_dms is None:
            return {"found": False, "lat": None, "lon": None, "altitude": None, "error": None}

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)

        # Optional altitude
        alt = None
        alt_raw = gps_tags.get("GPSAltitude")
        if alt_raw is not None:
            try:
                alt = round(float(alt_raw), 2)
            except (TypeError, ValueError):
                alt = None

        return {"found": True, "lat": round(lat, 7), "lon": round(lon, 7),
                "altitude": alt, "error": None}

    except Exception as exc:  # noqa: BLE001
        return {"found": False, "lat": None, "lon": None, "altitude": None,
                "error": f"EXIF read error: {exc}"}


# ──────────────────────────────────────────────────────────────────────────────
# Haversine distance helper (metres)
# ──────────────────────────────────────────────────────────────────────────────

_EARTH_RADIUS_M = 6_371_000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two WGS-84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


# ──────────────────────────────────────────────────────────────────────────────
# Main verification entry point
# ──────────────────────────────────────────────────────────────────────────────

def verify_geotag(image_path: str, submitted_lat: float, submitted_lon: float) -> dict:
    """
    Extract EXIF GPS and compare with submitted coordinates.

    Returns a dict:
      status         : "VERIFIED" | "MISMATCH" | "NO_EXIF_GPS" | "EXTRACTION_ERROR"
      exif_lat       : float or None
      exif_lon       : float or None
      exif_altitude  : float or None
      distance_m     : float or None   (distance between EXIF and submitted, in metres)
      threshold_m    : float           (configured max allowed distance)
      message        : str             (human-readable summary)
    """
    max_dist = float(
        current_app.config.get("GEOTAG_MAX_DISTANCE_METERS", 200.0)
    )

    gps = extract_exif_gps(image_path)

    if gps["error"] and not gps["found"]:
        return {
            "status": "EXTRACTION_ERROR",
            "exif_lat": None,
            "exif_lon": None,
            "exif_altitude": None,
            "distance_m": None,
            "threshold_m": max_dist,
            "message": gps["error"],
        }

    if not gps["found"]:
        return {
            "status": "NO_EXIF_GPS",
            "exif_lat": None,
            "exif_lon": None,
            "exif_altitude": None,
            "distance_m": None,
            "threshold_m": max_dist,
            "message": "Image contains no GPS EXIF metadata. Coordinates accepted from form input.",
        }

    dist = haversine_distance(gps["lat"], gps["lon"], submitted_lat, submitted_lon)
    dist = round(dist, 2)

    if dist <= max_dist:
        status = "VERIFIED"
        message = (
            f"EXIF GPS coordinates verified. "
            f"Distance between photo metadata and submitted pin: {dist:.1f} m "
            f"(within {max_dist:.0f} m threshold)."
        )
    else:
        status = "MISMATCH"
        message = (
            f"EXIF GPS mismatch detected. "
            f"Photo metadata location is {dist:.1f} m from submitted pin "
            f"(threshold: {max_dist:.0f} m). Manual review recommended."
        )

    return {
        "status": status,
        "exif_lat": gps["lat"],
        "exif_lon": gps["lon"],
        "exif_altitude": gps["altitude"],
        "distance_m": dist,
        "threshold_m": max_dist,
        "message": message,
    }
