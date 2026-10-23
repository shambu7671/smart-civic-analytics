from datetime import datetime, timedelta, timezone
from flask import Blueprint, request
from sqlalchemy import func
from app import db
from app.models.report import Report
from app.models.issue import Issue
from app.models.category import IssueCategory
from app.models.duplicate import DuplicateCandidate
from app.utils.api import success
from app.utils.security import require_role

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/admin")


@analytics_bp.get("/analytics")
@require_role("ADMIN")
def admin_analytics():
    total_reports = Report.query.count()
    total_issues = Issue.query.count()

    pending_verification = Issue.query.filter(Issue.status.in_(["REPORTED", "UNDER_REVIEW"])).count()
    high_priority_issues = Issue.query.filter_by(priority_level="HIGH").count()
    resolved_issues = Issue.query.filter_by(status="RESOLVED").count()
    duplicate_reports_detected = DuplicateCandidate.query.count()

    avg_reports = round(total_reports / total_issues, 2) if total_issues > 0 else 0.0

    cat_counts = (
        db.session.query(IssueCategory.name, func.count(Issue.id))
        .outerjoin(Issue, Issue.category_id == IssueCategory.id)
        .group_by(IssueCategory.name)
        .all()
    )
    issues_by_category = [{"category": name, "count": count} for name, count in cat_counts]

    priority_order = ["HIGH", "MEDIUM", "LOW"]
    p_counts = dict(
        db.session.query(Issue.priority_level, func.count(Issue.id))
        .group_by(Issue.priority_level)
        .all()
    )
    issues_by_priority = [{"priority": p, "count": p_counts.get(p, 0)} for p in priority_order]

    status_order = ["REPORTED", "UNDER_REVIEW", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"]
    s_counts = dict(
        db.session.query(Issue.status, func.count(Issue.id))
        .group_by(Issue.status)
        .all()
    )
    issues_by_status = [{"status": s, "count": s_counts.get(s, 0)} for s in status_order]

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=29)).date()

    dates_map = {}
    for i in range(30):
        d_str = (start_date + timedelta(days=i)).isoformat()
        dates_map[d_str] = 0

    reports_window = Report.query.filter(
        Report.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    ).all()
    for r in reports_window:
        if r.created_at:
            d_str = r.created_at.date().isoformat()
            if d_str in dates_map:
                dates_map[d_str] += 1

    reports_over_time = [{"date": d, "count": dates_map[d]} for d in sorted(dates_map.keys())]

    data = {
        "total_reports": total_reports,
        "total_issues": total_issues,
        "pending_verification": pending_verification,
        "high_priority_issues": high_priority_issues,
        "resolved_issues": resolved_issues,
        "duplicate_reports_detected": duplicate_reports_detected,
        "average_reports_per_issue": avg_reports,
        "issues_by_category": issues_by_category,
        "issues_by_priority": issues_by_priority,
        "issues_by_status": issues_by_status,
        "reports_over_time": reports_over_time,
    }
    return success(data, "Admin analytics retrieved.")
