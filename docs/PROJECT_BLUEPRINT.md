# Smart Civic System — Detailed Project Blueprint

This document explains the project from the user journey down to its modules, data model, APIs, configuration, and current implementation limits. It is based on the code in this repository. It can be used as a project walkthrough, presentation guide, or viva preparation document.

## 1. Project at a glance

Smart Civic System is a web application for collecting location-based civic problem reports and managing them through an administrative workflow. Its current AI-supported scope is road issues: potholes, road damage, and road cracks. A report contains a citizen's description, category, severity, photo, and coordinates.

The key design idea is to distinguish a **report** from an **issue**:

- A **report** is one citizen's evidence and observation.
- An **issue** is the civic problem that municipal staff need to manage. Several reports may support one issue.

The goal is to reduce repeated complaints into a manageable issue queue while preserving each citizen's report and its evidence.

### One-sentence summary

Citizens submit a photo and location for a road problem; the system checks and enriches the report, compares it with nearby submissions, groups reports into civic issues, calculates a configurable priority, and lets administrators track the work through resolution.

## 2. Actors and outcomes

### Citizen

Can register or sign in, submit a report, see their own reports, inspect linked civic issues, and follow issue status and history. A citizen's API access is constrained to reports/issues connected to that citizen, except for the read-only public map.

### Administrator

Can review reports and duplicate candidates, inspect and edit issues, verify and assign issues, update issue status, run clustering, view maps and analytics, inspect users, and change system settings.

### Public visitor

Can visit informational pages and the public map. The public map returns selected issue summaries for operational statuses and omits report-owner identity.

## 3. Architecture and request path

```text
Browser pages (Jinja templates + JavaScript + CSS)
          |  JSON requests / multipart photo upload
          v
Flask application factory and blueprints
          |  auth, role checks, CSRF checks, validation
          v
Route handlers (HTTP input/output and access rules)
          v
Service layer (image, geotag, language, AI, duplicate,
               clustering, priority, settings, storage)
          v
SQLAlchemy / GeoAlchemy2
          v
PostgreSQL + PostGIS       Optional private Supabase Storage
```

The browser layer is mostly server-rendered HTML with page-specific JavaScript. The Flask routes expose both HTML pages and JSON APIs. SQLAlchemy models represent the relational data. PostGIS provides geographic point storage and distance queries.

### Application startup

`run.py` is the local development launcher. When executed directly, it tries to connect to PostgreSQL at `127.0.0.1:5432`; if unreachable, it attempts to start a PostgreSQL 18 installation at a fixed Windows path, then starts Flask on `127.0.0.1:5000`. When imported, it creates the Flask app without that local database-start routine. `wsgi.py` exposes `app` for a WSGI server.

`app/__init__.py:create_app()` loads environment configuration, points Flask at the repository-level `static/` directory and `app/templates/`, initializes SQLAlchemy, registers blueprints, installs a read-only-demo write guard and security context helper, registers error handlers, and (unless skipped for tests) calls `db.create_all()` and seeds any missing default categories/settings.

`db.create_all()` creates absent tables. It does not migrate already-existing columns; the separate migration script exists for schema evolution.

## 4. Main end-to-end flow

### 4.1 Sign-in and session

The browser obtains a CSRF token through the Flask session and sends it in `X-CSRF-Token` for protected state-changing calls. The backend stores the user ID and role in the signed Flask session cookie. Passwords use Werkzeug password hashing.

Regular local registration and login use a unique full name and password. Registration generates an internal placeholder email because the form does not collect email. Optional local demo login creates/selects a configured citizen or admin identity and marks the session read-only. The Firebase helper code is not wired into the active login route.

### 4.2 Report submission

The citizen form sends category ID, description, severity, latitude, longitude, selected language, and an image as multipart form data. The report route:

1. Requires login and validates the CSRF token.
2. Checks allowed image extension and MIME type, category, coordinates, description, and severity.
3. Saves a sanitized, randomly named photo and confirms that OpenCV can decode it.
4. Optionally uploads the photo to private Supabase Storage when configured; otherwise it keeps the local file.
5. Extracts photo EXIF GPS when available and compares it with the submitted map point.
6. Detects the description language and attempts rule-based normalization into English.
7. Adds a recommended department and action based on category and selected display language.
8. Stores the `Report` with its PostGIS geography point and geotag result.
9. Runs AI detection, nearby duplicate scoring, and DBSCAN clustering. These are invoked synchronously in the request, with exception handling around the later processing stages.
10. Returns a serialized report, including AI/geotag results and any issue link.

If `GEOTAG_ENFORCEMENT_MODE=strict`, an EXIF/submitted coordinate mismatch blocks submission. The default `warn` mode stores the report and records the mismatch.

### 4.3 AI result

The AI service supports two modes:

- `demo`: derives a canned result from the selected category. It does not analyze the photo. The response is labelled `DEMO_DETECTED` / `DEMO-MOCK-YOLO`; this is demonstration behavior, not a model prediction or accuracy result.
- `real`: attempts to load an Ultralytics YOLO checkpoint, decode the image, convert BGR to RGB, and predict. It stores the highest-confidence box/category. Missing checkpoint, package, or inference errors are caught and stored as `UNAVAILABLE`.

One AI detection row is stored per report. Subsequent calls return the existing row rather than recomputing it.

### 4.4 Duplicate candidate analysis

The duplicate service uses PostGIS `ST_DWithin` to retrieve up to 50 nearby reports inside a configurable radius. For each candidate it computes:

- Geographic closeness, scaled from distance and search radius.
- Category match (same category is 1, otherwise 0).
- Image similarity using a small grayscale/blur/resize and bounded image-difference comparison.
- Description similarity using TF-IDF vectors and cosine similarity. It compares translated/normalized text when available.

The weighted score is normalized by the sum of configured weights. Candidates above the candidate threshold are stored as `PENDING` for an administrator. This is a transparent heuristic, not a learned duplicate classifier.

### 4.5 Clustering and unified issues

The clustering service groups reports by category, converts latitude/longitude to radians, and runs Scikit-learn DBSCAN with the haversine metric. The configured epsilon is converted from metres to angular radians using an Earth-radius constant.

Reports receive or retain a link in `issue_reports`. A cluster without a pre-existing linked issue creates a new issue. Existing links can be consolidated into a canonical issue, with its location updated to the cluster's arithmetic mean and its description chosen from the longest report description. Unclustered noise reports receive individual issue records if they do not already have one.

After clustering, each issue's supporting-report count and priority are recalculated. Clustering runs after every submission and can also be triggered manually by an administrator.

### 4.6 Priority

The priority service normalizes four factors to the 0–1 range:

- Severity: citizen or administrator severity from 1 to 5.
- Report support: diminishing-return curve based on number of linked reports.
- Age: issue age scaled to 30 days.
- Location importance: 1 to 5.

The configured weights are divided by their total, then the result is multiplied by 100. Configurable cutoffs map the score to `LOW`, `MEDIUM`, or `HIGH`. These values are operational configuration for a prototype, not empirically validated policy weights.

### 4.7 Administrative workflow and citizen tracking

Administrators can inspect the report inbox and duplicate candidates; verify, assign, or edit a unified issue; update status; and inspect the assignment and status audit lists. Status transitions create `issue_status_history` rows with actor, old/new status, timestamp, and remarks. Marking an issue resolved also sets `resolved_at` and completes open assignments.

Citizens can retrieve only issues linked to at least one of their reports. Issue details include supporting reports, assignment information, and status history subject to that authorization check.

### 4.8 Maps and analytics

The administrator GIS endpoints filter issue points by category, priority, status, and time window. Map and heatmap responses are capped at 1,000 issues. The public endpoints expose only issues in `VERIFIED`, `ASSIGNED`, `IN_PROGRESS`, or `RESOLVED` states and return summary location/status/priority data without citizen identities.

Analytics include report/issue totals, pending and resolved counts, duplicate-candidate count, category/priority/status summaries, average reports per issue, and a 30-day report timeline.

## 5. Database blueprint

Spatial report and issue columns use `GEOGRAPHY(POINT,4326)`, with GiST indexes. The SQLAlchemy models are in `app/models/`; the explicit PostgreSQL schema is `database/schema.sql`.

| Table / model | Purpose | Important relationships |
|---|---|---|
| `users` / `User` | Citizen and admin identity, local password hash, role, contact fields, optional Firebase UID | One user to many reports; actor/reviewer on audit records |
| `issue_categories` / `IssueCategory` | Active/inactive category definitions | One category to reports and issues |
| `reports` / `Report` | Individual citizen evidence, text, image reference, coordinates, severity, language and geotag fields | Belongs to user and category; may have one AI row and one issue link |
| `ai_detections` / `AIDetection` | Model name/version, result, confidence, box, status, timing | One-to-one with report |
| `duplicate_candidates` / `DuplicateCandidate` | Pair of reports and component/overall scores plus review decision | References new/existing report and optional admin reviewer |
| `issues` / `Issue` | Unified operational civic problem, priority, location, status | Has linked reports, assignments, and status history |
| `issue_reports` / `IssueReport` | Join record linking one report to one issue and recording link method | `report_id` is unique, so each report links to at most one issue |
| `issue_status_history` / `IssueStatusHistory` | Auditable status transition | Belongs to issue; records user who changed it |
| `issue_assignments` / `IssueAssignment` | Department/person assignment and completion time | Belongs to issue |
| `system_settings` / `SystemSetting` | Database-backed thresholds and weights | Read by setting service and editable through admin API |

The schema also enables row-level security and revokes Supabase `anon` / `authenticated` API access to these tables. The Flask server is expected to connect with its database credentials.

### Relationships in compact form

```text
User 1 ── N Report N ── 1 IssueCategory
Report 1 ── 0..1 AIDetection
Report 1 ── N DuplicateCandidate (new or existing side)
Report 1 ── 0..1 IssueReport N ── 1 Issue
Issue 1 ── N IssueStatusHistory
Issue 1 ── N IssueAssignment
```

## 6. Backend module map

### `app/routes/`

- `auth.py`: register, local login, optional demo login, logout, current-user endpoint.
- `reports.py`: language helper endpoint, citizen report create/list/detail/statistics, report AI alias, serialization.
- `ai.py`: canonical AI detect endpoint `/api/ai/detect/<report_id>`.
- `issues.py`: citizen/admin issue listing and issue detail serialization/access rules.
- `admin.py`: report review, issues, duplicate review actions, verification, status, assignment, issue editing, users, settings, audit listings, manual clustering.
- `map.py`: admin-only issue map and heatmap data APIs.
- `public_map.py`: public read-only issue map and heatmap APIs.
- `analytics.py`: admin analytics aggregation.
- `pages.py`: HTML page routes, category API, protected photo serving.
- `health.py`: `/health` and `/api/health` database/PostGIS probes.

### `app/services/`

- `ai_service.py`: demo and real YOLO boundary plus persisted result/fallback.
- `image_service.py`: secure local image save/decode, image similarity, storage integration and image reference handling.
- `supabase_storage_service.py`: private object upload/download/delete and `supabase://` references.
- `firebase_service.py`: optional Firebase Admin and legacy Storage/token helper code; not the current local login flow.
- `geotag_service.py`: EXIF GPS extraction, distance comparison and status generation.
- `translation_service.py`: script/vocabulary heuristics for English/Hindi/Marathi, dictionary normalization, and localized category/department/action/status labels.
- `duplicate_service.py`: PostGIS candidate query and weighted component scores.
- `clustering_service.py`: DBSCAN and report-to-issue reconciliation.
- `priority_service.py`: score normalization and priority level assignment.
- `setting_service.py`: retrieve/update database setting values.
- `seed_service.py`: seed active and future categories plus system defaults when missing.

### `app/utils/`

- `security.py`: password hash verification, CSRF token comparison, login/role decorators, session user lookup.
- `validators.py`: image extension/MIME checks, coordinate ranges, password length.
- `api.py`: uniform JSON success/error wrappers.
- `errors.py`: consistent API/page handlers for oversized upload, not found, forbidden, and server errors.
- `helpers.py`: UTC/date conversion, numeric clamping, and safe stored-image filename extraction.

### Root Python entry/config files

- `run.py`: local Windows launcher plus app entry point.
- `wsgi.py`: WSGI server import target.
- `app/config.py`: environment-backed Flask/database/upload/AI/storage/geotag/session settings.
- `requirements.txt`: main runtime and test dependencies.
- `requirements.training.txt`: additional YOLO/PyTorch packages for model training/inference.
- `.env.example`: documented local configuration template. The real `.env` contains local values and should not be shared.

## 7. Browser pages and frontend modules

The templates live in `app/templates/`. The application uses the root-level `static/` directory as its configured static folder; a similarly named `app/static/` tree is also present and appears to duplicate frontend assets, so changes should be checked against the configured root `static/` copy.

### Page groups

- Public: home, about, contact, login/register, public map.
- Citizen: dashboard, report form, report list/detail, issue detail, profile, tracking.
- Admin: dashboard, reports, issues/detail, duplicates, map, analytics, users, assignments, status history, settings.

### JavaScript modules

- `app.js`: shared API request, CSRF, navigation, message, badge, and pagination helpers.
- `auth.js`: registration/login/demo login UI interactions.
- `report-form.js`: category selection, location/GPS/map interaction, language and multipart submission.
- `citizen.js`, `report-detail.js`, `issue-detail.js`, `profile.js`, `tracking.js`: citizen dashboard, report/issue display, profile, and tracking views.
- `public-map.js`, `map.js`: public/admin Leaflet map data and filters; admin map includes heatmap behavior.
- `admin.js`, `admin-reports.js`, `admin-issues.js`, `admin-issue-detail.js`, `admin-duplicates.js`: administrator tables and issue/report review actions.
- `analytics.js`: Chart.js dashboard charts.
- `users.js`, `assignments.js`, `status.js`, `settings.js`: admin lists and settings editor.
- `i18n.js`: locale loading and text selection.
- `accessibility.js`: accessibility-oriented UI enhancements.

CSS is in `static/css/app.css`. Locale JSON files for English, Hindi, and Marathi are in `static/locales/`.

## 8. API blueprint

Successful responses use `{success, message, data}` and may include `meta` for pagination. Errors use `{success:false, message, error}`.

| Area | Routes | Access / use |
|---|---|---|
| Authentication | `POST /api/auth/register`, `/login`, `/logout`; `GET /api/auth/me`; `POST /api/auth/demo-login`, `/admin-demo-login` | Register/login establish session; mutation calls require CSRF; demos depend on config |
| Categories/language | `GET /api/categories`; `POST /api/reports/detect-language` | Active categories and language normalization helper |
| Citizen reports | `POST /api/reports`; `GET /api/reports/my`, `/my/stats`, `/<id>`; `POST /api/reports/<id>/ai` | Login; owner checks for citizen data; multipart create |
| AI | `POST /api/ai/detect/<report_id>` | Login, owner/admin check, CSRF |
| Issues | `GET /api/issues`, `GET /api/issues/<id>` | Login; citizens see only issues linked to their reports |
| Admin reports | `GET /api/admin/reports`; `PATCH /api/admin/reports/<id>` | Admin; list/filter and report submission status |
| Admin issues | `GET /api/admin/issues`; `PATCH /api/admin/issues/<id>` | Admin; list/filter, update issue fields |
| Admin workflow | `POST /api/admin/issues/<id>/verify`, `/assign`, `/status` | Admin workflow mutations |
| Duplicate review | `GET /api/admin/duplicates`; `POST /api/admin/duplicates/<id>/confirm`, `/reject`, `/separate` | Admin candidate review |
| Admin tools | `POST /api/admin/clustering/run`; `GET /api/admin/users`, `/settings`, `/assignments`, `/status-history`; `PATCH /api/admin/settings/<key>` | Admin tools and audit views |
| Analytics | `GET /api/admin/analytics` | Admin dashboard summaries |
| Admin GIS | `GET /api/map/issues`, `/heatmap` | Admin filters by category, priority, status, date |
| Public GIS | `GET /api/public/map/issues`, `/heatmap` | Public summary of operational issue statuses |
| Health | `GET /health`, `/api/health` | Database and PostGIS readiness check |

Page URLs and API routes are distinct: the HTML page routes in `pages.py` render screens; their JavaScript calls the JSON APIs above.

## 9. Configuration and important defaults

Configuration is loaded from `.env` through `app/config.py`. The following are representative defaults from `.env.example`:

| Setting | Default | Effect |
|---|---:|---|
| `AI_MODE` | `demo` | Select demo output or real YOLO path |
| `AI_MODEL_PATH` | `ai/models/best.pt` | Checkpoint path for real inference |
| `MAX_UPLOAD_SIZE_MB` | `8` | Flask request body limit |
| `DUPLICATE_RADIUS_METERS` | `100` | Nearby report search radius |
| `DUPLICATE_CANDIDATE_THRESHOLD` | `0.45` | Minimum score stored for review |
| `DBSCAN_EPS_METERS` | `80` | DBSCAN neighborhood radius |
| `DBSCAN_MIN_SAMPLES` | `2` | DBSCAN minimum points for a core cluster |
| Priority weights | `.35/.25/.20/.20` | Severity/report count/age/location importance |
| Priority thresholds | `70/45` | High/medium boundaries |
| Geotag maximum distance | `200 m` | EXIF/submitted pin mismatch limit |
| `GEOTAG_ENFORCEMENT_MODE` | `warn` | Warn/store or reject mismatched photo |
| `LOCAL_DEMO_LOGIN_ENABLED` | `true` locally | Enables read-only local demo sessions; disabled when `FLASK_ENV=production` |
| Supabase values | empty | When set, enables private remote photo storage |

Some settings are read from the database after seeding, while others are read directly from Flask configuration. Review the exact service call before assuming an admin-edited database value controls every similarly named environment setting.

## 10. Database initialization, migrations, and demo data

### Base schema

`database/schema.sql` enables PostGIS and defines tables, constraints, indexes, and public API role revocations. `database/seed.sql` inserts basic categories/settings. Application startup also creates missing tables and seeds missing records.

### Migrations

`scripts/migrate.py` applies its explicit SQL migration list and tracks completed migration IDs in `_schema_migrations`, then calls `db.create_all()`. It currently includes geotag, translation, PostGIS, and Firebase identity migrations. SQL files under `database/migrations/` document Supabase-related operations but are not automatically consumed by `scripts/migrate.py`.

### Demo seeder

Run `scripts/seed_demo.py` only against a disposable local demo database and only after setting `ALLOW_DEMO_SEED=true`. It deletes rows for core users/reports/issues and related workflow data, resets some sequences, generates synthetic images, creates demo users and 20 reports across 8 intended location/category groups, runs AI and clustering, and adds sample workflow states and duplicate candidates. It intentionally creates synthetic academic evidence, not real street photos.

## 11. AI model workflow

`ai/training/rdd2022.yaml` describes a locally supplied road-damage dataset layout. The repository does not download the dataset. `ai/training/train_yolo.py` uses Ultralytics to train a YOLO model from a compatible local dataset and base checkpoint. `ai/inference/predict_image.py` is a standalone inference example. Runtime dependencies in `requirements.training.txt` are separate from the core application requirements.

The included training and inference scripts are examples. A compatible dataset export, trained checkpoint, and evaluation are still required before reporting meaningful model quality.

## 12. Tests and what they cover

- `test_validation.py`: coordinate, password-length, and extension/MIME validation helpers.
- `test_services.py`: text/category/image similarity behavior, meter/radian configuration contract, priority score bounds.
- `test_api_contract.py`: public page rendering, protected admin page behavior, health endpoints.
- `test_integration_notes.py`: static acceptance checklist marker, not a real workflow test.
- `test_integration_postgis.py`: intended opt-in end-to-end PostGIS workflow against a separate database when environment variables are set.

The PostGIS integration test's login helper currently sends an `email` field to an endpoint that expects `name`; as written, that test helper is inconsistent with the current authentication implementation. The test is also destructive to its configured test database (`drop_all()`), so it must only target an isolated test database.

## 13. Security and privacy controls in the code

- Password hashes are generated and checked with Werkzeug.
- Session authorization and role checks protect citizen/admin pages and APIs.
- CSRF validation exists as a reusable helper and is called for many state-changing routes.
- Upload names are sanitized and randomized; MIME/extension and actual image decoding are checked.
- Flask request size limit bounds uploads.
- Report photos are served through an authenticated route that checks whether the requester owns the report or is an admin; remote storage access is mediated by the server.
- Demo sessions are blocked from write requests by a global before-request guard.
- Public map responses omit citizen identity and only include selected issue summaries.
- SQL uses bound parameters in the PostGIS nearby query.

This is a prototype baseline, not a full production security review. In particular, duplicate confirm/reject/separate handlers in `admin.py` use admin role checks but do not call `require_csrf()` themselves, unlike several other mutation routes. State-changing handlers should be audited for consistent CSRF enforcement. Production deployment also needs HTTPS/secure cookies, secret management, rate limiting, logging/monitoring, and operational backup controls.

## 14. Current limitations and code/design differences

1. **Demo AI is synthetic.** It keys off the citizen-selected category and does not inspect pixels.
2. **Language processing is heuristic.** `translation_service.py` uses script/word heuristics and a civic phrase dictionary; it is not a general machine translation service. Untranslated Devanagari characters may be stripped during normalization.
3. **Priority is configurable but not scientifically validated.** The score is a prototype ranking aid, not an official service-level rule.
4. **Duplicate scoring is a heuristic.** Image comparison is simple, TF-IDF is lexical, and candidates are intended for review.
5. **Several thresholds are currently declarative or inconsistently consumed.** `DUPLICATE_AUTO_LINK_THRESHOLD` and image/text threshold settings are seeded/configured but are not visibly used by the central report-linking logic. Candidate threshold reads Flask config rather than the database setting service.
6. **Clustering may override review decisions.** The all-reports rerun can consolidate issue links that already exist. A previously separated or admin-reviewed relationship may therefore need protection from automatic re-clustering.
7. **Clustering is synchronous and global.** Every submission reloads and reclusters all reports. This is simple for a small prototype but has poor scaling characteristics.
8. **The first report in a category is special-cased.** When that category has a single report, clustering assigns it label 0 even if configured `min_samples` is greater than 1; it therefore receives an issue immediately.
9. **Some write routes need a CSRF consistency review.** See the security section.
10. **The app has two static asset trees.** Flask is configured to serve root `static/`; `app/static/` duplicates many assets and can confuse edits/builds.
11. **Authentication docs are partly stale.** Current normal login uses full name/password; active auth routes do not verify Firebase credentials, even though Firebase helper code and migration history remain.
12. **Startup is machine-specific.** The automatic database startup in `run.py` assumes a fixed PostgreSQL 18 Windows path and should not be treated as portable deployment logic.
13. **Automatic table creation is not a schema upgrade mechanism.** Existing databases need migrations for new columns.

## 15. Suggested presentation order

1. Explain the problem: repeated citizen complaints make municipal triage difficult.
2. Introduce the report/issue distinction.
3. Show the user roles and pages.
4. Walk one report through validation, image/GPS storage, language enrichment, and AI result.
5. Explain nearby duplicate scoring and DBSCAN grouping, stressing that these are decision-support heuristics.
6. Show the issue priority factors and administrator workflow.
7. Explain the database relationships and PostGIS use.
8. Demonstrate citizen tracking, admin map, public map, and analytics.
9. State demo/real AI differences and current limitations accurately.
10. Finish with setup, seed data, tests, and realistic future work.

## 16. Short viva explanation

“Smart Civic System is a location-aware civic reporting prototype. A citizen submits a road issue with a photo, category, description, severity, and GPS point. The backend validates the input, records the report in PostgreSQL/PostGIS, checks available photo GPS metadata, and adds language and department guidance. It can return a clearly labelled demo AI result or use a supplied YOLO checkpoint. It searches nearby reports and compares location, category, image, and text signals to create duplicate candidates. DBSCAN groups reports by category and distance into unified civic issues. A configurable score ranks issues using severity, supporting report count, age, and location importance. Administrators verify, assign, and update issues, with status history retained for citizen tracking and audit. Maps and analytics expose operational summaries. The system is a prototype: demo AI is not a trained detector, similarity and priority weights need empirical evaluation, and the clustering workflow needs safeguards before production use.”

## 17. Quick run reference

1. Install Python dependencies from `requirements.txt`.
2. Install and start PostgreSQL with PostGIS; create the target database and enable the extension.
3. Copy `.env.example` to `.env` and set a private `SECRET_KEY` and correct `DATABASE_URL`.
4. Start with `python run.py` and open `http://127.0.0.1:5000`.
5. For sample data, point to a disposable local database, set `ALLOW_DEMO_SEED=true`, and run `python scripts/seed_demo.py`.
6. Use citizen/admin demo login for a read-only walk-through, or normal local accounts to exercise write flows.

Use `pytest -q` for the local test suite. Only run the opt-in PostGIS integration test with `RUN_POSTGIS_TESTS=1` and a dedicated `TEST_DATABASE_URL`.
