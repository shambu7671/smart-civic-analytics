from math import exp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import text
from flask import current_app
from app import db
from app.models.report import Report
from app.models.duplicate import DuplicateCandidate
from app.services.image_service import perceptual_similarity
from app.services.setting_service import get_setting


def text_similarity(a, b):
    docs = [(a or "").strip(), (b or "").strip()]
    if not docs[0] or not docs[1]:
        return 0.0
    vec = TfidfVectorizer(stop_words="english")
    try:
        matrix = vec.fit_transform(docs)
    except ValueError:
        return 0.0
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


def category_similarity(a, b):
    return 1.0 if a.category_id == b.category_id else 0.0


def location_candidates(report):
    radius = get_setting("DUPLICATE_RADIUS_METERS", current_app.config["DUPLICATE_RADIUS_METERS"], float)
    sql = text("""
        SELECT r.id
        FROM reports r
        WHERE r.id <> :rid
          AND ST_DWithin(r.location_geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius)
        ORDER BY ST_Distance(r.location_geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
        LIMIT 50
    """)
    ids = [row[0] for row in db.session.execute(sql, {"rid": report.id, "lon": report.longitude, "lat": report.latitude, "radius": radius})]
    return Report.query.filter(Report.id.in_(ids)).all() if ids else []


def distance_meters(a, b):
    row = db.session.execute(text("""
        SELECT ST_Distance(
            ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography,
            ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)::geography
        )
    """), {"lon1": a.longitude, "lat1": a.latitude, "lon2": b.longitude, "lat2": b.latitude}).scalar_one()
    return float(row)


def overall_score(distance, category, image, text_score):
    radius = get_setting("DUPLICATE_RADIUS_METERS", current_app.config["DUPLICATE_RADIUS_METERS"], float)
    location_score = max(0.0, min(1.0, 1.0 - distance / max(radius, 1.0)))
    weights = {
        "location": get_setting("DUPLICATE_LOCATION_WEIGHT", 0.30, float),
        "category": get_setting("DUPLICATE_CATEGORY_WEIGHT", 0.20, float),
        "image": get_setting("DUPLICATE_IMAGE_WEIGHT", 0.30, float),
        "text": get_setting("DUPLICATE_TEXT_WEIGHT", 0.20, float),
    }
    total = sum(weights.values()) or 1.0
    return ((location_score * weights["location"] + category * weights["category"] + image * weights["image"] + text_score * weights["text"]) / total)


def analyze_duplicates(report):
    candidates = []
    for existing in location_candidates(report):
        dist = distance_meters(report, existing)
        cat = category_similarity(report, existing)
        image = perceptual_similarity(report.image_path, existing.image_path)
        # Compare normalized English text for accurate cross-lingual duplicate matching
        text_a = getattr(report, 'translated_text', None) or report.description
        text_b = getattr(existing, 'translated_text', None) or existing.description
        txt = text_similarity(text_a, text_b)
        score = overall_score(dist, cat, image, txt)
        if score >= current_app.config.get("DUPLICATE_CANDIDATE_THRESHOLD", 0.45):
            already = DuplicateCandidate.query.filter_by(new_report_id=report.id, existing_report_id=existing.id).first()
            if already:
                continue
            cand = DuplicateCandidate(
                new_report_id=report.id,
                existing_report_id=existing.id,
                distance_meters=dist,
                category_similarity=cat,
                image_similarity=image,
                text_similarity=txt,
                overall_similarity=score,
                decision="PENDING",
            )
            db.session.add(cand)
            candidates.append(cand)
    db.session.commit()
    return candidates
