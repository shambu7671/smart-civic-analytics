from datetime import datetime, timezone
from flask import Blueprint, request
from app.models.issue import Issue
from app.models.issue_report import IssueReport
from app.models.audit import IssueStatusHistory
from app.models.report import Report
from app.utils.api import success, error
from app.utils.security import require_login, current_user_id
from app.models.user import User
from app.services.priority_service import recalculate_issue_priority, refresh_issue_priorities
from app import db
from app.utils.helpers import stored_image_filename

issues_bp = Blueprint("issues", __name__, url_prefix="/api/issues")


def serialize_issue(issue, include_reports=False):
    payload = {
        "id": issue.id, "issue_code": issue.issue_code, "category": issue.category.name,
        "description": issue.description, "latitude": issue.latitude, "longitude": issue.longitude,
        "severity": issue.severity, "severity_source": issue.severity_source,
        "report_count": issue.report_count, "age_score": round(issue.age_score, 2), "age_days": round(max(0.0, (datetime.now(timezone.utc) - (issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at.tzinfo is None else issue.created_at)).total_seconds() / 86400.0), 2),
        "location_importance": issue.location_importance, "priority_score": issue.priority_score,
        "priority_level": issue.priority_level, "status": issue.status,
        "created_at": issue.created_at.isoformat(), "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
    }
    if include_reports:
        links = IssueReport.query.filter_by(issue_id=issue.id).all()
        payload["supporting_reports"] = [
            {"id": x.report.id, "description": x.report.description, "latitude": x.report.latitude, "longitude": x.report.longitude,
             "image_url": f"/uploads/{stored_image_filename(x.report.image_path)}", "link_method": x.link_method, "created_at": x.report.created_at.isoformat(), "user_id": x.report.user_id,
             "ai": {"status": x.report.ai_detection.status if x.report.ai_detection else "PENDING", "detected_category": x.report.ai_detection.detected_category if x.report.ai_detection else None, "confidence_score": x.report.ai_detection.confidence_score if x.report.ai_detection else None, "model_name": x.report.ai_detection.model_name if x.report.ai_detection else None, "processing_time_ms": x.report.ai_detection.processing_time_ms if x.report.ai_detection else None}}
            for x in links
        ]
        payload["primary_image_url"] = payload["supporting_reports"][0]["image_url"] if links else None
        payload["assignments"] = [{"assigned_to": a.assigned_to, "department": a.department, "remarks": a.remarks, "assigned_at": a.assigned_at.isoformat(), "completed_at": a.completed_at.isoformat() if a.completed_at else None} for a in issue.assignments]
        payload["status_history"] = [
            {"old_status": x.old_status, "new_status": x.new_status, "remarks": x.remarks, "changed_by": x.changed_by, "changed_by_name": x.user.name if x.user else None, "changed_at": x.changed_at.isoformat()}
            for x in issue.status_history
        ]
    return payload


@issues_bp.get("")
@require_login
def list_issues():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    status = request.args.get("status")
    priority = request.args.get("priority")
    category = request.args.get("category")
    query = Issue.query
    user = User.query.get(current_user_id())
    if user.role == "CITIZEN":
        query = query.join(IssueReport).join(Report).filter(Report.user_id == user.id)
    if status:
        query = query.filter(Issue.status == status)
    if priority:
        query = query.filter(Issue.priority_level == priority)
    if category:
        query = query.join(Issue.category).filter_by(slug=category)
    query = query.order_by(Issue.created_at.desc())
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    refresh_issue_priorities(pagination.items)
    return success([serialize_issue(i) for i in pagination.items], "Issues retrieved successfully.", page=page, limit=limit, total=pagination.total, pages=pagination.pages)


@issues_bp.get("/<int:issue_id>")
@require_login
def issue_detail(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    user = User.query.get(current_user_id())
    if user.role == "CITIZEN":
        owns = db.session.query(IssueReport.id).join(Report).filter(IssueReport.issue_id == issue.id, Report.user_id == user.id).first()
        if not owns:
            return error("You are not allowed to view this issue.", status=403)
    recalculate_issue_priority(issue)
    db.session.commit()
    return success(serialize_issue(issue, include_reports=True), "Issue retrieved successfully.")
