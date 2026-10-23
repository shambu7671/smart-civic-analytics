from flask import Blueprint, request
from app.models.issue import Issue
from app.utils.api import success
from app.services.priority_service import refresh_issue_priorities

public_map_bp = Blueprint('public_map', __name__, url_prefix='/api/public/map')


def _issues():
    query = Issue.query.filter(Issue.status.in_(['VERIFIED','ASSIGNED','IN_PROGRESS','RESOLVED']))
    category = request.args.get('category')
    if category and category != 'all':
        query = query.join(Issue.category).filter_by(slug=category)
    return query.order_by(Issue.created_at.desc()).limit(1000).all()

@public_map_bp.get('/issues')
def public_issues():
    rows = _issues()
    refresh_issue_priorities(rows)
    return success([{'id': x.id, 'issue_code': x.issue_code, 'category': x.category.name, 'latitude': x.latitude, 'longitude': x.longitude, 'report_count': x.report_count, 'priority_score': x.priority_score, 'priority_level': x.priority_level, 'status': x.status} for x in rows], 'Public civic map issues retrieved.')

@public_map_bp.get('/heatmap')
def public_heatmap():
    rows = _issues()
    refresh_issue_priorities(rows)
    return success([[x.latitude,x.longitude,max(0.1,x.priority_score/100.0)] for x in rows], 'Public civic heatmap retrieved.')
