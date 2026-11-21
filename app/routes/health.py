"""
Health check and system status endpoint.
Registered as /health and /api/health.
Used by local health checks and uptime monitors.
"""
from datetime import datetime, timezone
import logging
from flask import Blueprint
from sqlalchemy import text
from app import db

health_bp = Blueprint("health", __name__)
logger = logging.getLogger(__name__)


@health_bp.get("/health")
def health_check():
    """
    Lightweight liveness + readiness probe.
    Returns HTTP 200 if app + DB are healthy, 503 otherwise.
    """
    status = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
    http_status = 200

    # Database probe
    try:
        db.session.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception:
        logger.exception("Health check database probe failed")
        status["database"] = "unavailable"
        status["status"] = "degraded"
        http_status = 503

    # PostGIS probe
    try:
        db.session.execute(text("SELECT PostGIS_version()"))
        status["postgis"] = "ok"
    except Exception:
        logger.exception("Health check PostGIS probe failed")
        status["postgis"] = "unavailable"
        # PostGIS unavailable is degraded but not fatal for basic operation
        if http_status == 200:
            status["status"] = "degraded"
            http_status = 503

    return status, http_status


@health_bp.get("/api/health")
def api_health():
    """Alias for /health — used by API clients."""
    return health_check()
