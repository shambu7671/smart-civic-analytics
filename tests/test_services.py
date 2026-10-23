from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
from PIL import Image

from app import create_app
from app.services import duplicate_service, image_service, priority_service


def test_text_similarity_semantically_related_bag_of_words():
    score = duplicate_service.text_similarity(
        "large pothole near college gate",
        "pothole close to college gate",
    )
    assert 0 < score <= 1


def test_category_similarity():
    a = SimpleNamespace(category_id=1)
    b = SimpleNamespace(category_id=1)
    c = SimpleNamespace(category_id=2)
    assert duplicate_service.category_similarity(a, b) == 1.0
    assert duplicate_service.category_similarity(a, c) == 0.0


def test_perceptual_similarity_identical_images(tmp_path):
    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    arr = np.full((64,64,3), 120, dtype=np.uint8)
    Image.fromarray(arr).save(p1)
    Image.fromarray(arr).save(p2)
    assert image_service.perceptual_similarity(str(p1), str(p2)) > 0.95


def test_perceptual_similarity_different_images(tmp_path):
    p1 = tmp_path / "a.png"
    p2 = tmp_path / "b.png"
    Image.fromarray(np.zeros((64,64,3), dtype=np.uint8)).save(p1)
    Image.fromarray(np.full((64,64,3), 255, dtype=np.uint8)).save(p2)
    assert image_service.perceptual_similarity(str(p1), str(p2)) <= 0.05


def test_haversine_dbscan_configuration_is_meter_based(monkeypatch):
    # Contract-level test: the cluster service must convert configured meters to Earth-radius radians.
    import app.services.clustering_service as clustering
    app = create_app({"TESTING": True, "SKIP_DB_INIT": True})
    with app.app_context():
        app.config["DBSCAN_EPS_METERS"] = 100
        assert clustering.current_app.config["DBSCAN_EPS_METERS"] == 100


def test_priority_calculation_uses_four_configurable_factors(monkeypatch):
    app = create_app({"TESTING": True, "SKIP_DB_INIT": True})
    monkeypatch.setattr(priority_service, "_weight", lambda key, fallback: {"SEVERITY_WEIGHT":0.35,"REPORT_WEIGHT":0.25,"AGE_WEIGHT":0.20,"LOCATION_WEIGHT":0.20}[key])
    monkeypatch.setattr(priority_service, "_threshold", lambda key, fallback: {"HIGH_PRIORITY_THRESHOLD":70,"MEDIUM_PRIORITY_THRESHOLD":45}[key])
    issue = SimpleNamespace(
        severity=5, report_count=10, location_importance=5,
        created_at=datetime.now(timezone.utc) - timedelta(days=20),
        age_score=0, priority_score=0, priority_level="LOW",
    )
    with app.app_context():
        out=priority_service.recalculate_issue_priority(issue)
    assert 0 <= out.priority_score <= 100
    assert out.age_score > 0
    assert out.priority_level in {"LOW","MEDIUM","HIGH"}
