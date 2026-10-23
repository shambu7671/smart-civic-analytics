# File Manifest

## Root

- `run.py` — Flask development entry point.
- `requirements.txt` — pinned Python dependencies.
- `.env.example` — environment configuration template.
- `.gitignore` — excludes secrets, caches, uploads and model weights.
- `README.md` — full installation, database, AI, API, testing and troubleshooting guide.

## `app/`

- `__init__.py` — Flask application factory and blueprint registration.
- `config.py` — central environment-backed configuration.

### `app/models/`
- `user.py` — citizen/admin users.
- `category.py` — configurable civic issue categories.
- `report.py` — citizen report + PostGIS point.
- `issue.py` — unified civic issue + priority/state fields.
- `issue_report.py` — report-to-issue association.
- `ai_detection.py` — model result, confidence, bounding box and processing timing.
- `duplicate.py` — explainable duplicate-candidate signals and review decision.
- `audit.py` — status history, assignment and system settings.
- `__init__.py` — model exports.

### `app/routes/`
- `auth.py` — register/login/logout/session API.
- `reports.py` — report submission, citizen report listing/detail and AI alias.
- `ai.py` — canonical `/api/ai/detect/<report_id>` endpoint.
- `issues.py` — citizen/admin issue retrieval.
- `admin.py` — administrator management APIs.
- `map.py` — authenticated administrator GIS/heatmap APIs.
- `public_map.py` — read-only public civic map APIs with no citizen identity.
- `analytics.py` — dashboard analytics API.
- `pages.py` — browser page routes and protected upload serving.

### `app/services/`
- `ai_service.py` — DEMO or real YOLO inference with failure fallback.
- `image_service.py` — secure image saving and explainable image similarity.
- `duplicate_service.py` — PostGIS proximity + category/image/text similarity.
- `clustering_service.py` — DBSCAN using haversine/geographic distance.
- `priority_service.py` — configurable priority scoring.
- `setting_service.py` — database-backed configuration access.
- `seed_service.py` — initial categories and settings.

### `app/utils/`
- `api.py` — consistent JSON success/error responses.
- `security.py` — session, password hashing, CSRF, RBAC.
- `validators.py` — coordinate/password/image validation.
- `errors.py` — human-readable Flask/API error handlers.
- `helpers.py` — general helper functions.

## Frontend

- `static/css/app.css` — responsive civic-tech styling.
- `static/js/app.js` — shared API, alert, badge, pagination and navigation helpers.
- `static/js/auth.js` — registration/login.
- `static/js/report-form.js` — upload/GPS/map report form.
- `static/js/citizen.js` — citizen dashboard and report list.
- `static/js/report-detail.js` — report details.
- `static/js/issue-detail.js` — citizen issue details/timeline.
- `static/js/profile.js` — profile panel.
- `static/js/tracking.js` — issue tracking list.
- `static/js/public-map.js` — public civic map.
- `static/js/admin.js` — admin dashboard and DBSCAN action.
- `static/js/admin-reports.js` — report review table.
- `static/js/admin-issues.js` — issue filters/table.
- `static/js/admin-issue-detail.js` — issue verification/status/assignment.
- `static/js/admin-duplicates.js` — duplicate review.
- `static/js/map.js` — admin GIS map/filter/heatmap.
- `static/js/analytics.js` — Chart.js analytics.
- `static/js/users.js` — user table.
- `static/js/assignments.js` — assignment history.
- `static/js/status.js` — status audit history.
- `static/js/settings.js` — configuration editor + DBSCAN action.

## AI

- `ai/training/rdd2022.yaml` — example road-damage dataset config.
- `ai/training/train_yolo.py` — local YOLO training entry point.
- `ai/inference/predict_image.py` — local YOLO inference example.
- `ai/models/.gitkeep` — checkpoint directory marker.

## Database

- `database/schema.sql` — explicit PostGIS DDL.
- `database/seed.sql` — base categories and system settings.
- `scripts/seed_demo.py` — secure-password synthetic demo dataset: 10 citizens, 20 reports, 8 clustered issue groups.

## Tests

- `tests/test_validation.py` — input validation tests.
- `tests/test_services.py` — similarity/priority/clustering configuration tests.
- `tests/test_api_contract.py` — public/protected route checks.
- `tests/test_integration_notes.py` — acceptance-contract marker.
- `tests/test_integration_postgis.py` — optional real PostgreSQL/PostGIS end-to-end workflow.

## Documentation

- `docs/ARCHITECTURE.md` — A–H architecture, ER, data flow and viva explanation.
