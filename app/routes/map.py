from datetime import datetime, timedelta, timezone
from flask import Blueprint, request
from app.models.issue import Issue
from app.utils.api import success
from app.utils.security import require_role
from app.services.priority_service import refresh_issue_priorities

map_bp = Blueprint("map", __name__, url_prefix="/api/map")


def _query_issues():
    query = Issue.query
    category = request.args.get("category")
    priority = request.args.get("priority")
    status = request.args.get("status")
    days = request.args.get("days")
    if category and category != "all":
        query = query.join(Issue.category).filter_by(slug=category)
    if priority and priority != "all":
        query = query.filter(Issue.priority_level == priority.upper())
    if status and status != "all":
        query = query.filter(Issue.status == status.upper())
    if days and days != "custom":
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
            query = query.filter(Issue.created_at >= cutoff)
        except ValueError:
            pass
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if days == "custom" and start_date:
        try:
            start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            query = query.filter(Issue.created_at >= start_dt)
        except ValueError:
            pass
    if days == "custom" and end_date:
        try:
            end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
            query = query.filter(Issue.created_at < end_dt)
        except ValueError:
            pass
    return query.order_by(Issue.created_at.desc())


@map_bp.get("/issues")
@require_role("ADMIN")
def map_issues():
    issues = _query_issues().limit(1000).all()
    refresh_issue_priorities(issues)
    return success([{"id": i.id, "issue_code": i.issue_code, "category": i.category.name, "category_slug": i.category.slug, "latitude": i.latitude, "longitude": i.longitude,
                     "report_count": i.report_count, "priority_score": i.priority_score, "priority_level": i.priority_level, "status": i.status} for i in issues], "Map issues retrieved.")


@map_bp.get("/heatmap")
@require_role("ADMIN")
def heatmap():
    issues = _query_issues().limit(1000).all()
    refresh_issue_priorities(issues)
    points = [[i.latitude, i.longitude, max(0.1, i.priority_score / 100.0)] for i in issues]
    return success(points, "Heatmap points retrieved.")
