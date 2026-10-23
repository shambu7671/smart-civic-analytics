from pathlib import Path
from datetime import datetime, timezone
import time
import cv2
from flask import current_app
from app import db
from app.models.ai_detection import AIDetection
from app.models.category import IssueCategory


def _demo_detect(report):
    # Deterministic demo behaviour derived from the requested category. It is explicitly labelled DEMO.
    category = report.category.name if report.category else "Other / Manual Review"
    if category in {"Pothole", "Road Damage", "Road Crack"}:
        # Demo score is intentionally not described as model accuracy.
        confidence = 0.91 if category == "Pothole" else 0.78
        return {
            "model_name": "DEMO-MOCK-YOLO",
            "model_version": "demo-1",
            "detected_category": category,
            "confidence_score": confidence,
            "status": "DEMO_DETECTED",
            "bounding_box": None,
        }
    return {
        "model_name": "DEMO-MOCK-YOLO",
        "model_version": "demo-1",
        "detected_category": None,
        "confidence_score": 0.0,
        "status": "MANUAL_REVIEW",
        "bounding_box": None,
    }


def _real_detect(report):
    model_path = Path(current_app.config["AI_MODEL_PATH"])
    if not model_path.exists():
        raise FileNotFoundError(str(model_path))
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Ultralytics is not installed.") from exc

    model = YOLO(str(model_path))
    from app.services.image_service import _read_image
    image = _read_image(report.image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not read report image for AI inference.")
    # Basic OpenCV preprocessing boundary: decode, normalize channel order, then hand the image to YOLO.
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model.predict(source=image, conf=current_app.config["AI_CONFIDENCE_THRESHOLD"], verbose=False)
    best = None
    for result in results:
        names = result.names
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            conf = float(box.conf[0])
            class_id = int(box.cls[0])
            label = names[class_id]
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            if best is None or conf > best["confidence_score"]:
                best = {
                    "model_name": "YOLO",
                    "model_version": model_path.stem,
                    "detected_category": label,
                    "confidence_score": conf,
                    "status": "DETECTED" if conf >= current_app.config["AI_CONFIDENCE_THRESHOLD"] else "MANUAL_REVIEW",
                    "bounding_box": xyxy,
                }
    return best or {
        "model_name": "YOLO",
        "model_version": model_path.stem,
        "detected_category": None,
        "confidence_score": 0.0,
        "status": "MANUAL_REVIEW",
        "bounding_box": None,
    }


def detect_report(report):
    existing = AIDetection.query.filter_by(report_id=report.id).first()
    if existing:
        return existing
    mode = current_app.config["AI_MODE"]
    started = time.perf_counter()
    try:
        result = _demo_detect(report) if mode == "demo" else _real_detect(report)
    except Exception as exc:
        result = {
            "model_name": "UNAVAILABLE",
            "model_version": "N/A",
            "detected_category": None,
            "confidence_score": 0.0,
            "status": "UNAVAILABLE",
            "bounding_box": None,
        }
    elapsed_ms = (time.perf_counter() - started) * 1000
    row = AIDetection(report_id=report.id, processed_at=datetime.now(timezone.utc), processing_time_ms=round(elapsed_ms, 2), **result)
    db.session.add(row)
    db.session.commit()
    return row
