from flask import Blueprint
from app.models.report import Report
from app.models.user import User
from app.services.ai_service import detect_report
from app.utils.api import success, error
from app.utils.security import require_login, require_csrf, current_user_id

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.post('/detect/<int:report_id>')
@require_login
def detect(report_id):
    require_csrf()
    report = Report.query.get_or_404(report_id)
    user = User.query.get(current_user_id())
    if user.role != 'ADMIN' and report.user_id != user.id:
        return error('Access denied.', status=403)
    row = detect_report(report)
    return success({
        'report_id': report.id,
        'status': row.status,
        'detected_category': row.detected_category,
        'confidence_score': row.confidence_score,
        'model_name': row.model_name,
        'model_version': row.model_version,
        'bounding_box': row.bounding_box,
        'processed_at': row.processed_at.isoformat() if row.processed_at else None,
        'processing_time_ms': row.processing_time_ms,
    }, 'AI processing completed.')
