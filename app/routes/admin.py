from datetime import datetime, timezone
from flask import Blueprint, request
from sqlalchemy import or_, func
from app import db
from app.models.user import User
from app.models.report import Report
from app.models.issue import Issue
from app.models.category import IssueCategory
from app.models.issue_report import IssueReport
from app.models.duplicate import DuplicateCandidate
from app.models.audit import IssueStatusHistory, IssueAssignment, SystemSetting
from app.services.clustering_service import cluster_all_reports, _new_issue_from_report
from app.services.priority_service import recalculate_issue_priority, refresh_issue_priorities
from app.utils.api import success, error
from app.utils.security import require_role, require_csrf, current_user_id
from app.routes.issues import serialize_issue
from app.utils.helpers import stored_image_filename

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

VALID_STATUSES = {"REPORTED", "UNDER_REVIEW", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"}


def report_image_url(report):
    return f"/uploads/{stored_image_filename(report.image_path)}"


def audit_status(issue, new_status, remarks=None):
    old = issue.status
    if old == new_status:
        return
    issue.status = new_status
    if new_status == "RESOLVED":
        issue.resolved_at = datetime.now(timezone.utc)
        for assignment in issue.assignments:
            if assignment.completed_at is None:
                assignment.completed_at = issue.resolved_at
    elif old == "RESOLVED":
        issue.resolved_at = None
    db.session.add(IssueStatusHistory(issue_id=issue.id, old_status=old, new_status=new_status, changed_by=current_user_id(), remarks=remarks))


@admin_bp.get("/reports")
@require_role("ADMIN")
def admin_reports():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    search = (request.args.get("search") or "").strip()
    query = Report.query.order_by(Report.created_at.desc())
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Report.description.ilike(like), Report.id.cast(db.String).ilike(like)))
    p = query.paginate(page=page, per_page=limit, error_out=False)
    data = [
        {
            "id": r.id,
            "category": r.category.name,
            "description": r.description,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "submission_status": r.submission_status,
            "created_at": r.created_at.isoformat(),
            "image_url": report_image_url(r),
            # Geotag verification fields for admin triage
            "geotag_status": r.geotag_status or "PENDING",
            "geotag_distance_m": r.geotag_distance_m,
        }
        for r in p.items
    ]
    return success(data, "Admin reports retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)



@admin_bp.patch("/reports/<int:report_id>")
@require_role("ADMIN")
def patch_report(report_id):
    require_csrf()
    report = Report.query.get_or_404(report_id)
    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "").upper()
    allowed = {"SUBMITTED", "UNDER_REVIEW", "VERIFIED", "REJECTED"}
    if status not in allowed:
        return error("Invalid report status.")
    report.submission_status = status
    db.session.commit()
    return success({"id": report.id, "submission_status": report.submission_status}, "Report status updated.")


@admin_bp.get("/issues")
@require_role("ADMIN")
def admin_issues():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    search = (request.args.get("search") or "").strip()
    category = (request.args.get("category") or "").strip()
    status = (request.args.get("status") or "").strip().upper()
    priority = (request.args.get("priority") or "").strip().upper()
    report_id = (request.args.get("report_id") or "").strip()
    query = Issue.query
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Issue.issue_code.ilike(like), Issue.status.ilike(like)))
    if category:
        query = query.join(Issue.category).filter(IssueCategory.slug == category)
    if status:
        query = query.filter(Issue.status == status)
    if priority:
        query = query.filter(Issue.priority_level == priority)
    if report_id.isdigit():
        query = query.join(IssueReport).filter(IssueReport.report_id == int(report_id))
    query = query.order_by(Issue.created_at.desc())
    p = query.paginate(page=page, per_page=limit, error_out=False)
    refresh_issue_priorities(p.items)
    return success([serialize_issue(i) for i in p.items], "Admin issues retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)


@admin_bp.get("/duplicates")
@require_role("ADMIN")
def duplicates():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    p = DuplicateCandidate.query.order_by(DuplicateCandidate.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    return success([
        {"id": x.id, "new_report_id": x.new_report_id, "existing_report_id": x.existing_report_id, "distance_meters": round(x.distance_meters, 2),
         "category_similarity": round(x.category_similarity, 3), "image_similarity": round(x.image_similarity, 3), "text_similarity": round(x.text_similarity, 3),
         "overall_similarity": round(x.overall_similarity, 3), "decision": x.decision,
         "new_image_url": report_image_url(x.new_report), "existing_image_url": report_image_url(x.existing_report),
         "new_latitude": x.new_report.latitude, "new_longitude": x.new_report.longitude, "existing_latitude": x.existing_report.latitude, "existing_longitude": x.existing_report.longitude}
        for x in p.items
    ], "Duplicate candidates retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)


@admin_bp.post("/duplicates/<int:candidate_id>/confirm")
@require_role("ADMIN")
def confirm_duplicate(candidate_id):
    require_csrf()
    cand = DuplicateCandidate.query.get_or_404(candidate_id)
    cand.decision = "CONFIRMED"
    cand.reviewed_by = current_user_id()
    cand.reviewed_at = datetime.now(timezone.utc)
    new_link = IssueReport.query.filter_by(report_id=cand.new_report_id).first()
    existing_link = IssueReport.query.filter_by(report_id=cand.existing_report_id).first()
    if new_link and existing_link and new_link.issue_id != existing_link.issue_id:
        old_issue = new_link.issue
        target = existing_link.issue
        new_link.issue = target
        new_link.link_method = "DUPLICATE_MATCH"
        db.session.flush()
        old_issue.report_count = IssueReport.query.filter_by(issue_id=old_issue.id).count()
        if old_issue.report_count == 0:
            db.session.delete(old_issue)
        target.report_count = IssueReport.query.filter_by(issue_id=target.id).count()
        recalculate_issue_priority(target)
    db.session.commit()
    return success(message="Potential duplicate confirmed and reports unified.")


@admin_bp.post("/duplicates/<int:candidate_id>/reject")
@require_role("ADMIN")
def reject_duplicate(candidate_id):
    require_csrf()
    cand = DuplicateCandidate.query.get_or_404(candidate_id)
    cand.decision = "REJECTED"
    cand.reviewed_by = current_user_id()
    cand.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return success(message="Duplicate candidate rejected.")


@admin_bp.post("/duplicates/<int:candidate_id>/separate")
@require_role("ADMIN")
def separate_issue(candidate_id):
    require_csrf()
    cand = DuplicateCandidate.query.get_or_404(candidate_id)
    cand.decision = "SEPARATE_ISSUE"
    cand.reviewed_by = current_user_id()
    cand.reviewed_at = datetime.now(timezone.utc)
    new_link = IssueReport.query.filter_by(report_id=cand.new_report_id).first()
    existing_link = IssueReport.query.filter_by(report_id=cand.existing_report_id).first()
    if new_link and existing_link and new_link.issue_id == existing_link.issue_id:
        current_issue = new_link.issue
        db.session.delete(new_link)
        db.session.flush()
        new_issue = _new_issue_from_report(cand.new_report)
        current_issue.report_count = IssueReport.query.filter_by(issue_id=current_issue.id).count()
        if current_issue.report_count == 0:
            db.session.delete(current_issue)
        else:
            recalculate_issue_priority(current_issue)
        recalculate_issue_priority(new_issue)
    elif not new_link:
        _new_issue_from_report(cand.new_report)
    db.session.commit()
    return success(message="Reports recorded as separate issues.")


@admin_bp.post("/issues/<int:issue_id>/verify")
@require_role("ADMIN")
def verify_issue(issue_id):
    require_csrf()
    issue = Issue.query.get_or_404(issue_id)
    audit_status(issue, "VERIFIED", "Issue verified by administrator.")
    db.session.commit()
    return success(serialize_issue(issue), "Issue verified.")


@admin_bp.post("/issues/<int:issue_id>/status")
@require_role("ADMIN")
def set_status(issue_id):
    require_csrf()
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").upper()
    if new_status not in VALID_STATUSES:
        return error("Invalid issue status.")
    audit_status(issue, new_status, data.get("remarks"))
    db.session.commit()
    return success(serialize_issue(issue), "Issue status updated.")


@admin_bp.post("/issues/<int:issue_id>/assign")
@require_role("ADMIN")
def assign_issue(issue_id):
    require_csrf()
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    person = (data.get("assigned_to") or "").strip()
    department = (data.get("department") or "").strip()
    if not person or not department:
        return error("Assigned person and department are required.")
    db.session.add(IssueAssignment(issue_id=issue.id, assigned_to=person, department=department, remarks=data.get("remarks")))
    audit_status(issue, "ASSIGNED", "Issue assigned to responsible department/person.")
    db.session.commit()
    return success(serialize_issue(issue), "Issue assigned.")


@admin_bp.patch("/issues/<int:issue_id>")
@require_role("ADMIN")
def patch_issue(issue_id):
    require_csrf()
    issue = Issue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}
    if "severity" in data:
        severity = int(data["severity"])
        if severity < 1 or severity > 5:
            return error("Severity must be between 1 and 5.")
        issue.severity = severity
        issue.severity_source = "ADMIN"
    if "location_importance" in data:
        value = int(data["location_importance"])
        if value < 1 or value > 5:
            return error("Location importance must be between 1 and 5.")
        issue.location_importance = value
    if "description" in data and data["description"]:
        issue.description = str(data["description"]).strip()
    recalculate_issue_priority(issue)
    db.session.commit()
    return success(serialize_issue(issue), "Issue updated.")


@admin_bp.get("/users")
@require_role("ADMIN")
def users():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    p = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    return success([{"id": u.id, "name": u.name, "email": u.email, "mobile": u.mobile, "role": u.role, "created_at": u.created_at.isoformat()} for u in p.items], "Users retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)


@admin_bp.get("/settings")
@require_role("ADMIN")
def settings():
    rows = SystemSetting.query.order_by(SystemSetting.setting_key.asc()).all()
    return success([{"key": r.setting_key, "value": r.setting_value, "description": r.description} for r in rows], "Settings retrieved.")


@admin_bp.patch("/settings/<string:key>")
@require_role("ADMIN")
def update_setting(key):
    require_csrf()
    row = SystemSetting.query.filter_by(setting_key=key).first()
    if not row:
        return error("Setting not found.", status=404)
    value = (request.get_json(silent=True) or {}).get("value")
    if value is None:
        return error("Value is required.")
    row.setting_value = str(value)
    db.session.commit()
    return success({"key": row.setting_key, "value": row.setting_value}, "Setting updated.")


@admin_bp.get("/assignments")
@require_role("ADMIN")
def assignments():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    p = IssueAssignment.query.order_by(IssueAssignment.assigned_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    return success([{"id": a.id, "issue_id": a.issue_id, "issue_code": a.issue.issue_code if a.issue else None, "assigned_to": a.assigned_to, "department": a.department, "remarks": a.remarks, "assigned_at": a.assigned_at.isoformat(), "completed_at": a.completed_at.isoformat() if a.completed_at else None} for a in p.items], "Assignments retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)


@admin_bp.get("/status-history")
@require_role("ADMIN")
def status_history():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    p = IssueStatusHistory.query.order_by(IssueStatusHistory.changed_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    return success([{"id": h.id, "issue_id": h.issue_id, "issue_code": h.issue.issue_code if h.issue else None, "old_status": h.old_status, "new_status": h.new_status, "changed_by": h.changed_by, "changed_by_name": h.user.name if h.user else None, "remarks": h.remarks, "changed_at": h.changed_at.isoformat()} for h in p.items], "Status history retrieved.", page=page, limit=limit, total=p.total, pages=p.pages)


@admin_bp.post("/clustering/run")
@require_role("ADMIN")
def run_clustering():
    require_csrf()
    result = cluster_all_reports()
    return success(result, "DBSCAN clustering completed.")
