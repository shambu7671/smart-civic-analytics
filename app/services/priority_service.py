
from datetime import datetime, timezone
from flask import current_app
from app import db
from app.services.setting_service import get_setting


def _weight(key, fallback):
    return get_setting(key, current_app.config[fallback], float)


def _threshold(key, fallback):
    return get_setting(key, current_app.config[fallback], float)


def severity_norm(severity):
    return max(0.0, min(1.0, (int(severity) - 1) / 4.0))


def report_norm(count):
    # Diminishing returns so one extra report matters less at high counts.
    return max(0.0, min(1.0, 1.0 - pow(2.718281828, -count / 8.0)))


def age_norm(created_at):
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    return max(0.0, min(1.0, age_days / 30.0))


def location_norm(value):
    return max(0.0, min(1.0, (int(value) - 1) / 4.0))


def recalculate_issue_priority(issue):
    sw = _weight("SEVERITY_WEIGHT", "SEVERITY_WEIGHT")
    rw = _weight("REPORT_WEIGHT", "REPORT_WEIGHT")
    aw = _weight("AGE_WEIGHT", "AGE_WEIGHT")
    lw = _weight("LOCATION_WEIGHT", "LOCATION_WEIGHT")
    total = max(sw + rw + aw + lw, 1e-9)
    score = 100 * ((severity_norm(issue.severity) * sw + report_norm(issue.report_count) * rw + age_norm(issue.created_at) * aw + location_norm(issue.location_importance) * lw) / total)
    issue.age_score = age_norm(issue.created_at) * 100
    issue.priority_score = round(score, 2)
    high = _threshold("HIGH_PRIORITY_THRESHOLD", "HIGH_PRIORITY_THRESHOLD")
    med = _threshold("MEDIUM_PRIORITY_THRESHOLD", "MEDIUM_PRIORITY_THRESHOLD")
    issue.priority_level = "HIGH" if score >= high else ("MEDIUM" if score >= med else "LOW")
    return issue


def refresh_issue_priorities(issues, commit=True):
    for issue in issues:
        recalculate_issue_priority(issue)
    if commit:
        db.session.commit()
    return issues
