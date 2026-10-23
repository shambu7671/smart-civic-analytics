from flask import Blueprint, request, current_app
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from app import db
from app.models.report import Report
from app.models.category import IssueCategory
from app.models.issue_report import IssueReport
from app.models.issue import Issue
from app.services.ai_service import detect_report
from app.services.duplicate_service import analyze_duplicates
from app.services.clustering_service import cluster_all_reports
from app.services.image_service import save_image
from app.services.geotag_service import verify_geotag
from app.utils.api import success, error
from app.utils.security import require_login, require_csrf, current_user_id
from app.utils.validators import validate_image, valid_coordinates
from app.utils.helpers import stored_image_filename
from pathlib import Path


reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


from app.services.translation_service import (
    detect_language,
    translate_to_english,
    get_department_and_action,
    localize_metadata,
    LANGUAGES
)


def serialize_report(report, lang: str = None):
    issue_link = IssueReport.query.filter_by(report_id=report.id).first()
    ai = report.ai_detection
    target_lang = lang or request.args.get("lang") or report.selected_language or "en"

    # Base department and action
    dept_info = get_department_and_action(
        report.category.name if report.category else "Other / Manual Review",
        report.self_reported_severity,
        target_lang
    )

    data = {
        "id": report.id,
        "category": report.category.name,
        "description": report.description,
        "original_text": report.original_text or report.description,
        "translated_text": report.translated_text or report.description,
        "detected_language": report.detected_language or "en",
        "selected_language": report.selected_language or "en",
        "recommended_department": report.recommended_department or dept_info["department"],
        "suggested_action": report.suggested_action or dept_info["action"],
        "latitude": report.latitude,
        "longitude": report.longitude,
        "image_url": f"/uploads/{stored_image_filename(report.image_path)}",
        "submission_status": report.submission_status,
        "severity": report.self_reported_severity,
        "created_at": report.created_at.isoformat(),
        "issue_id": issue_link.issue_id if issue_link else None,
        "issue_code": issue_link.issue.issue_code if issue_link else None,
        "supporting_report_count": issue_link.issue.report_count if issue_link else None,
        "issue_status": issue_link.issue.status if issue_link else None,
        "issue_priority_level": issue_link.issue.priority_level if issue_link else None,
        "issue_priority_score": issue_link.issue.priority_score if issue_link else None,
        "ai": {
            "status": ai.status if ai else "PENDING",
            "detected_category": ai.detected_category if ai else None,
            "confidence_score": ai.confidence_score if ai else None,
            "model_name": ai.model_name if ai else None,
            "model_version": ai.model_version if ai else None,
            "bounding_box": ai.bounding_box if ai else None,
        },
        # ── Geotag / EXIF GPS verification result ─────────────────────────
        "geotag": {
            "status": report.geotag_status or "PENDING",
            "exif_lat": report.geotag_lat,
            "exif_lon": report.geotag_lon,
            "exif_altitude": report.geotag_altitude,
            "distance_m": report.geotag_distance_m,
            "message": report.geotag_message,
        },
    }
    return localize_metadata(data, target_lang)


@reports_bp.post("/detect-language")
def api_detect_language():
    data = request.get_json(silent=True) or {}
    text_input = (data.get("text") or "").strip()
    detected = detect_language(text_input)
    translated, _ = translate_to_english(text_input, detected)
    return success({
        "detected_language": detected,
        "language_name": LANGUAGES.get(detected, {}).get("name", detected),
        "translated_text": translated
    }, "Language detected.")


@reports_bp.post("")
@require_login
def create_report():
    require_csrf()
    image = request.files.get("image")
    valid, msg = validate_image(image)
    if not valid:
        return error(msg)
    description = (request.form.get("description") or "").strip()
    category_id = request.form.get("category_id")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    selected_lang = (request.form.get("selected_language") or "en").strip().lower()

    try:
        severity = int(request.form.get("severity") or 3)
    except (TypeError, ValueError):
        severity = 3
    if not description or not category_id or not valid_coordinates(latitude, longitude):
        return error("Category, description and valid GPS coordinates are required.")
    if severity < 1 or severity > 5:
        return error("Severity must be between 1 and 5.")
    category = IssueCategory.query.filter_by(id=category_id, active=True).first()
    if not category:
        return error("Selected category is invalid.")
    try:
        image_path, _, local_image_path = save_image(image)
    except ValueError as exc:
        return error(str(exc))

    # ── Geotag / EXIF GPS verification ─────────────────────────────────────
    submitted_lat = float(latitude)
    submitted_lon = float(longitude)
    geotag_result = {
        "status": "PENDING",
        "exif_lat": None,
        "exif_lon": None,
        "exif_altitude": None,
        "distance_m": None,
        "message": None,
    }
    try:
        gt = verify_geotag(local_image_path, submitted_lat, submitted_lon)
        geotag_result = {
            "status": gt["status"],
            "exif_lat": gt["exif_lat"],
            "exif_lon": gt["exif_lon"],
            "exif_altitude": gt["exif_altitude"],
            "distance_m": gt["distance_m"],
            "message": gt["message"],
        }
        # In STRICT mode a MISMATCH blocks the submission with a 422 response.
        enforcement = current_app.config.get("GEOTAG_ENFORCEMENT_MODE", "warn")
        if enforcement == "strict" and gt["status"] == "MISMATCH":
            import os as _os
            try:
                _os.unlink(local_image_path)
            except OSError:
                pass
            if image_path.startswith("supabase://"):
                try:
                    from app.services.supabase_storage_service import delete_image, parse_storage_reference
                    bucket, object_key = parse_storage_reference(image_path)
                    delete_image(object_key, bucket=bucket)
                except Exception:
                    current_app.logger.warning("Could not remove rejected report photo from Supabase Storage.")
            return error(
                f"Photo location does not match the submitted map pin "
                f"(distance: {gt['distance_m']:.0f} m, max allowed: "
                f"{gt['threshold_m']:.0f} m). "
                "Please upload a photo taken at the reported location.",
                status=422,
            )
    except Exception as exc:
        current_app.logger.warning(
            "Geotag verification error for upload %s: %s", image_path, exc
        )
        geotag_result["status"] = "EXTRACTION_ERROR"
        geotag_result["message"] = str(exc)
    # ────────────────────────────────────────────────────────────────────────

    # Multilingual processing & normalisation
    detected_lang = detect_language(description, fallback=selected_lang)
    translated_text, _ = translate_to_english(description, source_lang=detected_lang)
    dept_info = get_department_and_action(category.name, severity, lang=selected_lang)

    report = Report(
        user_id=current_user_id(),
        category_id=category.id,
        description=description,
        original_text=description,
        translated_text=translated_text,
        detected_language=detected_lang,
        selected_language=selected_lang,
        recommended_department=dept_info["department"],
        suggested_action=dept_info["action"],
        image_path=image_path,
        latitude=submitted_lat,
        longitude=submitted_lon,
        location_geometry=WKTElement(
            f"POINT({submitted_lon} {submitted_lat})", srid=4326
        ),
        submission_status="SUBMITTED",
        self_reported_severity=severity,
        # Persist all geotag verification fields
        geotag_status=geotag_result["status"],
        geotag_lat=geotag_result["exif_lat"],
        geotag_lon=geotag_result["exif_lon"],
        geotag_altitude=geotag_result["exif_altitude"],
        geotag_distance_m=geotag_result["distance_m"],
        geotag_message=geotag_result["message"],
    )
    try:
        db.session.add(report)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Failed to save report: %s", exc)
        if image_path.startswith(("http://", "https://", "gs://", "supabase://")):
            import os as _os
            try:
                _os.unlink(local_image_path)
            except OSError:
                pass
            if image_path.startswith("supabase://"):
                try:
                    from app.services.supabase_storage_service import delete_image, parse_storage_reference
                    bucket, object_key = parse_storage_reference(image_path)
                    delete_image(object_key, bucket=bucket)
                except Exception:
                    current_app.logger.warning("Could not clean up orphaned Supabase report photo.")
        return error("Failed to save report. Please try again.")
    try:
        ai = detect_report(report)
        if ai.status in {"MANUAL_REVIEW", "UNAVAILABLE"}:
            report.submission_status = "UNDER_REVIEW"
            db.session.commit()
    except Exception as exc:
        current_app.logger.error("AI detection failed for report %s: %s", report.id, exc)
    try:
        analyze_duplicates(report)
    except Exception as exc:
        current_app.logger.error("Duplicate analysis failed for report %s: %s", report.id, exc)
    try:
        cluster_all_reports()
    except Exception as exc:
        current_app.logger.error("Clustering failed after report %s: %s", report.id, exc)
    if image_path.startswith(("http://", "https://", "gs://", "supabase://")):
        import os as _os
        try:
            _os.unlink(local_image_path)
        except OSError:
            pass
    return success(serialize_report(report, lang=selected_lang), "Report submitted successfully.", 201)


@reports_bp.get("/my")
@require_login
def my_reports():
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))
    query = Report.query.filter_by(user_id=current_user_id()).order_by(Report.created_at.desc())
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    return success(
        [serialize_report(r) for r in pagination.items],
        "Reports retrieved successfully.",
        page=page, limit=limit, total=pagination.total, pages=pagination.pages
    )


@reports_bp.get("/my/stats")
@require_login
def my_report_stats():
    from app.models.user import User
    user = User.query.get(current_user_id())
    total = Report.query.filter_by(user_id=user.id).count()
    issue_links = IssueReport.query.join(Report).filter(Report.user_id == user.id).all()
    resolved = sum(1 for x in issue_links if x.issue.status == "RESOLVED")
    verified = sum(1 for x in issue_links if x.issue.status in {"VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED"})
    pending = total - resolved - verified
    return success(
        {"total_reports": total, "pending": pending, "verified_issues": verified, "resolved_issues": resolved},
        "Report statistics retrieved."
    )


@reports_bp.get("/<int:report_id>")
@require_login
def get_report(report_id):
    report = Report.query.get_or_404(report_id)
    from app.models.user import User
    user = User.query.get(current_user_id())
    if user.role == "CITIZEN" and report.user_id != user.id:
        return error("You are not allowed to view this report.", status=403)
    return success(serialize_report(report), "Report retrieved successfully.")


@reports_bp.post("/<int:report_id>/ai")
@require_login
def ai_detect(report_id):
    require_csrf()
    report = Report.query.get_or_404(report_id)
    from app.models.user import User
    user = User.query.get(current_user_id())
    if user.role != "ADMIN" and report.user_id != user.id:
        return error("Access denied.", status=403)
    ai = detect_report(report)
    return success(
        {
            "status": ai.status,
            "detected_category": ai.detected_category,
            "confidence_score": ai.confidence_score,
            "model_name": ai.model_name,
            "model_version": ai.model_version,
            "bounding_box": ai.bounding_box,
        },
        "AI processing completed.",
    )
