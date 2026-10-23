from app import db
from app.models.category import IssueCategory
from app.models.audit import SystemSetting


def ensure_seed_categories_and_settings():
    categories = [
        ("Pothole", "pothole", True, "Surface depression or hole affecting road safety."),
        ("Road Damage", "road-damage", True, "Major road surface damage beyond a single crack/pothole."),
        ("Road Crack", "road-crack", True, "Visible cracking in the road surface."),
        ("Other / Manual Review", "manual-review", True, "Issue that requires manual categorisation."),
        ("Garbage Accumulation", "garbage", False, "Future category; disabled until a suitable model/workflow is added."),
        ("Broken Streetlight", "streetlight", False, "Future category; disabled until a suitable model/workflow is added."),
        ("Waterlogging", "waterlogging", False, "Future category; disabled until a suitable model/workflow is added."),
        ("Damaged Footpath", "footpath", False, "Future category; disabled until a suitable model/workflow is added."),
        ("Drainage Problem", "drainage", False, "Future category; disabled until a suitable model/workflow is added."),
    ]
    for name, slug, active, desc in categories:
        if not IssueCategory.query.filter_by(slug=slug).first():
            db.session.add(IssueCategory(name=name, slug=slug, active=active, description=desc))

    settings = {
        "DUPLICATE_RADIUS_METERS": ("100", "Nearby search radius used for duplicate candidates."),
        "DUPLICATE_AUTO_LINK_THRESHOLD": ("0.82", "Similarity above which a candidate is considered likely same issue; still reviewable."),
        "DUPLICATE_CANDIDATE_THRESHOLD": ("0.45", "Minimum overall similarity for creating a duplicate candidate."),
        "DUPLICATE_LOCATION_WEIGHT": ("0.30", "Duplicate score weight for geographic proximity."),
        "DUPLICATE_CATEGORY_WEIGHT": ("0.20", "Duplicate score weight for category match."),
        "DUPLICATE_IMAGE_WEIGHT": ("0.30", "Duplicate score weight for image similarity."),
        "DUPLICATE_TEXT_WEIGHT": ("0.20", "Duplicate score weight for description similarity."),
        "IMAGE_SIMILARITY_THRESHOLD": ("0.65", "Explainable image similarity threshold."),
        "TEXT_SIMILARITY_THRESHOLD": ("0.35", "TF-IDF cosine similarity threshold."),
        "DBSCAN_EPS_METERS": ("80", "DBSCAN geographic epsilon in meters."),
        "DBSCAN_MIN_SAMPLES": ("2", "DBSCAN minimum points per cluster."),
        "SEVERITY_WEIGHT": ("0.35", "Priority weight for 1-5 severity."),
        "REPORT_WEIGHT": ("0.25", "Priority weight for supporting report count."),
        "AGE_WEIGHT": ("0.20", "Priority weight for issue age."),
        "LOCATION_WEIGHT": ("0.20", "Priority weight for location importance."),
        "HIGH_PRIORITY_THRESHOLD": ("70", "Score at or above this value is HIGH."),
        "MEDIUM_PRIORITY_THRESHOLD": ("45", "Score at or above this value and below HIGH is MEDIUM."),
    }
    for key, (value, description) in settings.items():
        if not SystemSetting.query.filter_by(setting_key=key).first():
            db.session.add(SystemSetting(setting_key=key, setting_value=value, description=description))
    db.session.commit()
