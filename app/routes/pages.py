from io import BytesIO
import mimetypes
from pathlib import Path
from flask import Blueprint, render_template, abort, send_file, send_from_directory, current_app
from sqlalchemy import func
from app.models.category import IssueCategory
from app.models.user import User
from app.models.report import Report
from app.utils.api import success
from app.utils.security import require_role, current_user_id

pages_bp = Blueprint("pages", __name__)

@pages_bp.get("/")
def home(): return render_template("home.html")

@pages_bp.get("/about")
def about(): return render_template("about.html")

@pages_bp.get("/contact")
def contact(): return render_template("contact.html")

@pages_bp.get("/map")
def public_map_page(): return render_template("public_map.html")

@pages_bp.get("/login")
def login_page(): return render_template("auth/login.html")

@pages_bp.get("/register")
def register_page(): return render_template("auth/register.html")

@pages_bp.get("/citizen/dashboard")
@require_role("CITIZEN")
def citizen_dashboard(): return render_template("citizen/dashboard.html")

@pages_bp.get("/citizen/report")
@require_role("CITIZEN")
def report_page(): return render_template("citizen/report.html")

@pages_bp.get("/citizen/reports")
@require_role("CITIZEN")
def my_reports_page(): return render_template("citizen/reports.html")

@pages_bp.get("/citizen/reports/<int:report_id>")
@require_role("CITIZEN", "ADMIN")
def report_detail_page(report_id): return render_template("citizen/report_detail.html", report_id=report_id)

@pages_bp.get("/citizen/issues/<int:issue_id>")
@require_role("CITIZEN", "ADMIN")
def civic_issue_detail_page(issue_id): return render_template("citizen/issue_detail.html", issue_id=issue_id)

@pages_bp.get("/citizen/profile")
@require_role("CITIZEN")
def profile_page(): return render_template("citizen/profile.html")

@pages_bp.get("/citizen/tracking")
@require_role("CITIZEN")
def tracking_page(): return render_template("citizen/tracking.html")

@pages_bp.get("/admin/login")
def admin_login_page(): return render_template("auth/login.html", admin_login=True)

@pages_bp.get("/admin/dashboard")
@require_role("ADMIN")
def admin_dashboard_page(): return render_template("admin/dashboard.html")

@pages_bp.get("/admin/reports")
@require_role("ADMIN")
def admin_reports_page(): return render_template("admin/reports.html")

@pages_bp.get("/admin/issues")
@require_role("ADMIN")
def admin_issues_page(): return render_template("admin/issues.html")

@pages_bp.get("/admin/issues/<int:issue_id>")
@require_role("ADMIN")
def admin_issue_detail_page(issue_id): return render_template("admin/issue_detail.html", issue_id=issue_id)

@pages_bp.get("/admin/duplicates")
@require_role("ADMIN")
def admin_duplicates_page(): return render_template("admin/duplicates.html")

@pages_bp.get("/admin/map")
@require_role("ADMIN")
def admin_map_page(): return render_template("admin/map.html")

@pages_bp.get("/admin/analytics")
@require_role("ADMIN")
def admin_analytics_page(): return render_template("admin/analytics.html")

@pages_bp.get("/admin/users")
@require_role("ADMIN")
def admin_users_page(): return render_template("admin/users.html")

@pages_bp.get("/admin/assignments")
@require_role("ADMIN")
def admin_assignments_page(): return render_template("admin/assignments.html")

@pages_bp.get("/admin/status")
@require_role("ADMIN")
def admin_status_page(): return render_template("admin/status.html")

@pages_bp.get("/admin/settings")
@require_role("ADMIN")
def admin_settings_page(): return render_template("admin/settings.html")

@pages_bp.get("/uploads/<path:filename>")
@require_role("CITIZEN", "ADMIN")
def uploaded_file(filename):
    safe_name = Path(filename).name
    report = Report.query.filter(
        func.replace(Report.image_path, chr(92), "/").like(f"%/{safe_name}"),
    ).first()
    user = User.query.get(current_user_id())
    if not report or not user or (user.role != "ADMIN" and report.user_id != user.id):
        abort(404)
    if report.image_path.startswith(("http://", "https://", "gs://")):
        try:
            from app.services.firebase_service import download_image_bytes
            payload = download_image_bytes(
                f"uploads/{safe_name}",
                int(current_app.config.get("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)),
            )
        except Exception:
            abort(404)
        content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        response = send_file(BytesIO(payload), mimetype=content_type, download_name=safe_name)
    else:
        response = send_from_directory(current_app.config["UPLOAD_FOLDER"], safe_name)
    response.headers["Cache-Control"] = "private, no-store"
    return response

@pages_bp.get("/api/categories")
def categories_api():
    rows = IssueCategory.query.filter_by(active=True).order_by(IssueCategory.id.asc()).all()
    return success([{"id": x.id, "name": x.name, "slug": x.slug, "description": x.description} for x in rows], "Categories retrieved.")
