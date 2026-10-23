# AI-Based Smart Civic Issue Detection and Complaint Analytics

A modular academic smart-city prototype for citizen civic reporting, AI-assisted road-damage detection, explainable duplicate analysis, geospatial clustering, unified issue creation, configurable priority scoring, GIS visualization and administrator workflow tracking.

## 1. Scope

Initial AI-supported categories are **Pothole**, **Road Damage**, and **Road Crack**. The database also supports future categories, but those are inactive until a suitable workflow/model is added. The application never claims to detect future categories automatically.

### Main workflow

Citizen report → image/GPS validation → AI inference or DEMO fallback → nearby report comparison → duplicate candidate creation → DBSCAN geospatial clustering → unified civic issue → configurable priority score → GIS/heatmap → admin verification/assignment/status → citizen tracking.

## 2. Architecture

```text
Browser (HTML/CSS/JavaScript + Bootstrap + Leaflet)
                  |
                  | REST/JSON + multipart upload
                  v
             Flask Application
       +----------+----------+-----------+
       |          |          |           |
      Auth      Reports    Issues     Admin/Analytics
       |          |          |           |
       +----------+----------+-----------+
                  |
           Service Layer
       +----------+----------+-----------+
       |          |          |           |
      AI       Duplicate  DBSCAN     Priority
     YOLO/      scoring   clustering   scoring
    OpenCV      TF-IDF    haversine    config
       |          |          |           |
       +----------+----------+-----------+
                  |
           SQLAlchemy + GeoAlchemy2
                  |
           PostgreSQL + PostGIS
```

## 3. Module architecture

- `app/routes/`: thin HTTP/API endpoints and authorization.
- `app/models/`: SQLAlchemy/PostGIS data models.
- `app/services/ai_service.py`: demo/real YOLO inference boundary.
- `app/services/duplicate_service.py`: geographic candidates + category + OpenCV image similarity + TF-IDF cosine text similarity.
- `app/services/clustering_service.py`: DBSCAN with haversine/geographic distance.
- `app/services/priority_service.py`: severity/report count/age/location importance normalization and configurable weights.
- `app/services/image_service.py`: secure filenames, readable-image validation, simple perceptual similarity.
- `app/services/seed_service.py`: configurable categories/system settings.
- `static/js/`: browser clients for citizen/admin pages.
- `database/`: explicit PostGIS schema and base seed SQL.
- `scripts/seed_demo.py`: complete local demo dataset generator.
- `tests/`: unit and contract-level tests that do not require a live PostgreSQL server.

## 4. Database ER structure

```text
USERS 1 --- N REPORTS N --- 1 ISSUE_CATEGORIES
REPORTS 1 --- 1 AI_DETECTIONS
REPORTS 1 --- 0..N DUPLICATE_CANDIDATES (as new/existing)
ISSUES 1 --- N ISSUE_REPORTS N --- 1 REPORTS
ISSUES 1 --- N ISSUE_STATUS_HISTORY
ISSUES 1 --- N ISSUE_ASSIGNMENTS
SYSTEM_SETTINGS (configuration key/value store)
```

Spatial columns use `GEOGRAPHY(POINT, 4326)` with GiST indexes for meter-based PostGIS searches.

## 5. REST API list

### Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Categories
- `GET /api/categories`

### Citizen reports / AI
- `POST /api/reports`
- `GET /api/reports/my?page=1&limit=20`
- `GET /api/reports/<id>`
- `POST /api/reports/<id>/ai`
- `POST /api/ai/detect/<id>` (canonical AI endpoint requested by the project specification)

### Civic issues
- `GET /api/issues`
- `GET /api/issues/<id>`

### Admin
- `GET /api/admin/reports`
- `PATCH /api/admin/reports/<id>`
- `GET /api/admin/issues`
- `PATCH /api/admin/issues/<id>`
- `POST /api/admin/issues/<id>/verify`
- `POST /api/admin/issues/<id>/assign`
- `POST /api/admin/issues/<id>/status`
- `GET /api/admin/duplicates`
- `POST /api/admin/duplicates/<id>/confirm`
- `POST /api/admin/duplicates/<id>/reject`
- `POST /api/admin/duplicates/<id>/separate`
- `POST /api/admin/clustering/run`
- `GET /api/admin/users`
- `GET /api/admin/settings`
- `PATCH /api/admin/settings/<key>`
- `GET /api/admin/analytics`

### GIS
- `GET /api/map/issues`
- `GET /api/map/heatmap`

### Public GIS
- `GET /api/public/map/issues`
- `GET /api/public/map/heatmap`

## 6. Page list

### Public
`/`, `/about`, `/login`, `/register`, `/contact`, `/map`

### Citizen (role-protected)
`/citizen/dashboard`, `/citizen/report`, `/citizen/reports`, `/citizen/reports/<id>`, `/citizen/issues/<id>`, `/citizen/profile`, `/citizen/tracking`

### Administrator (role-protected)
`/admin/login`, `/admin/dashboard`, `/admin/reports`, `/admin/issues`, `/admin/issues/<id>`, `/admin/duplicates`, `/admin/map`, `/admin/analytics`, `/admin/users`, `/admin/assignments`, `/admin/status`, `/admin/settings`

## 7. Data flow

1. Citizen registers and logs in.
2. Browser gets a CSRF token from the session and sends a multipart report.
3. Server validates category, description, coordinates, extension/MIME and actual image readability.
4. Report is stored with a PostGIS geography point.
5. AI service runs DEMO mode or a configured YOLO checkpoint.
6. Duplicate service searches nearby reports with `ST_DWithin` and calculates location, category, image and TF-IDF text similarities.
7. DBSCAN uses haversine coordinates and configurable meter epsilon/minimum samples.
8. Cluster members are linked into one `issues` row via `issue_reports`.
9. Priority score combines normalized severity, supporting report count, age and location importance using settings whose weights are normalized to sum to one at calculation time.
10. Admin UI verifies, assigns and transitions the issue through status history.
11. Leaflet and heatmap APIs query stored issue data.

## 8. Development order

1. PostgreSQL/PostGIS setup
2. Environment variables
3. Database schema/bootstrap
4. Run Flask app
5. Seed demo data
6. Test citizen registration/login
7. Submit a report with GPS/image
8. Inspect AI result and duplicate candidates
9. Run clustering
10. Verify/assign/status-change issue from admin
11. Test GIS and analytics
12. Add real YOLO checkpoint only after the rest of the workflow is stable

## 9. Installation — Windows / VS Code

### 9.1 Prerequisites

Install:
- Python 3.11+ recommended
- PostgreSQL 15+ recommended
- PostGIS extension compatible with your PostgreSQL version
- Git
- VS Code

### 9.2 Create the database

In `psql` or pgAdmin:

```sql
CREATE USER smartcity WITH PASSWORD 'smartcity';
CREATE DATABASE smart_civic OWNER smartcity;
GRANT ALL PRIVILEGES ON DATABASE smart_civic TO smartcity;
```

Connect to `smart_civic` and enable PostGIS:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

The application also creates required tables on startup, but `database/schema.sql` is provided for explicit database setup/review.

### 9.3 Python environment

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 9.4 Environment file

```powershell
copy .env.example .env
```

Edit `.env` and change at least:
- `SECRET_KEY`
- `DATABASE_URL`
- `AI_MODE`

For local student development, `AI_MODE=demo` is recommended until a real model checkpoint is available. `DATABASE_URL` and `SECRET_KEY` are intentionally environment-provided rather than hard-coded in Python.

Example:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg2://smartcity:smartcity@localhost:5432/smart_civic
AI_MODE=demo
AI_MODEL_PATH=ai/models/best.pt
```

### 9.5 Optional explicit SQL setup

For manual database review/setup:

```powershell
psql -U smartcity -d smart_civic -f database/schema.sql
psql -U smartcity -d smart_civic -f database/seed.sql
```

The Flask startup also creates missing tables and inserts missing categories/settings.

### 9.6 Start the app

```powershell
python run.py
```

Open `http://127.0.0.1:5000`.

## 10. Demo data

After PostgreSQL/PostGIS is running and the application is configured:

```powershell
$env:ALLOW_DEMO_SEED="true"
python scripts/seed_demo.py
```

This creates:
- 1 administrator
- 10 citizens
- 20 synthetic reports
- clustered/unified civic issues
- multiple supporting-report groups
- varied status, severity and location-importance values
- pending duplicate candidates
- synthetic report images

### Local demo credentials

**Administrator**
- Email: `admin@smartcivic.local`
- Password: `Admin@12345`

**Citizen**
- Email: `aarav@example.com`
- Password: `Citizen@12345`

These credentials are intended only for local academic demonstration.

## 11. AI / YOLO integration

### Demo mode

Set:

```dotenv
AI_MODE=demo
```

The UI marks results as `DEMO_DETECTED` and the model name as `DEMO-MOCK-YOLO`. These values are deterministic demonstration outputs and are **not model accuracy measurements**.

### Real mode

1. Place a trained YOLO checkpoint at the configured path, for example:
   `ai/models/best.pt`
2. Set:

```dotenv
AI_MODE=real
AI_MODEL_PATH=ai/models/best.pt
AI_CONFIDENCE_THRESHOLD=0.55
```

3. Restart the Flask application.

If the checkpoint or Ultralytics inference path is unavailable, the report still stays stored and AI status becomes `UNAVAILABLE` or `MANUAL_REVIEW`; the application does not crash the reporting workflow.

## 12. RDD2022 support

The repository does not automatically download any external dataset. A compatible road-damage dataset export can be placed under:

```text
ai/datasets/rdd2022/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

The example dataset configuration is `ai/training/rdd2022.yaml`. Adjust class names to match the exact annotation format of the dataset export you legally obtained. The example training script is `ai/training/train_yolo.py`.

## 13. Duplicate detection details

The score is an explainable weighted combination of:
- geographic proximity
- category match
- image similarity
- description text similarity

The geographic component is normalized from the configured radius. Image similarity is intentionally simple: grayscale resize + Gaussian blur + bounded MSE-based similarity. Text similarity uses TF-IDF + cosine similarity from Scikit-learn. The weights live in `system_settings` / `.env` and are not hard-coded into the frontend.

The application creates **potential duplicate** records rather than claiming absolute duplicate certainty. Administrators can confirm, reject or separate the candidate.

## 14. DBSCAN

`app/services/clustering_service.py` converts latitude/longitude to radians and runs Scikit-learn DBSCAN with `metric='haversine'`. `DBSCAN_EPS_METERS` is converted to angular radians using Earth radius. This avoids applying naive Euclidean distance to raw degree values.

## 15. Priority scoring

The four project factors are:

- severity (1–5)
- supporting report count
- issue age
- location importance (1–5)

Each factor is normalized to `[0,1]`. Configured weights are normalized by their total before the final 0–100 score is calculated. Thresholds for HIGH/MEDIUM are configurable.

Example defaults:

```text
Severity  0.35
Reports   0.25
Age       0.20
Location  0.20
```

These are prototype configuration values, not empirically validated civic-governance weights.

## 16. Status flow

Core synopsis flow:

`REPORTED → VERIFIED → RESOLUTION`

Implementation extension:

`REPORTED → UNDER_REVIEW → VERIFIED → ASSIGNED → IN_PROGRESS → RESOLVED`

`REJECTED` is supported as an administrative outcome.

Every important status transition is written to `issue_status_history` with actor, timestamp and remarks.

## 17. Security

Implemented in this prototype:
- Werkzeug password hashing
- session authentication
- role-based access control
- CSRF token checks on state-changing requests
- server-side input validation
- safe image filenames
- file extension/MIME checks
- OpenCV readable-image verification
- request upload-size limit
- no credentials hard-coded in application code
- protected report image endpoint
- admin-only analytics/settings/user-management endpoints

For production, add a reverse proxy/HTTPS, production secret management, rate limiting, stronger content scanning and operational logging.

## 18. API response format

Success:

```json
{
  "success": true,
  "message": "Issue retrieved successfully.",
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "message": "Invalid request",
  "error": "Human-readable error"
}
```

## 19. Testing

Run unit/contract tests:

```powershell
pytest -q
```

Run the real end-to-end PostGIS acceptance test against an isolated test database:

```powershell
$env:RUN_POSTGIS_TESTS="1"
$env:TEST_DATABASE_URL="postgresql+psycopg2://smartcity:smartcity@localhost:5432/smart_civic_test"
pytest -q tests/test_integration_postgis.py
```

The included tests intentionally avoid requiring a live PostGIS service so they can be run during development. Integration testing against a real PostgreSQL/PostGIS instance is still recommended before a final demonstration.

## 20. Complete workflow test

1. Start PostgreSQL + PostGIS.
2. Run `python run.py`.
3. Set `$env:ALLOW_DEMO_SEED="true"` and run `python scripts/seed_demo.py` against a local demo database only.
4. Login as the citizen demo account.
5. Open **Report Issue**.
6. Upload a JPG/PNG, enter a description, get GPS or click the map, submit.
7. Confirm the report and AI record exist.
8. Login as admin.
9. Open **Duplicate Review** and inspect stored component scores.
10. Open **Civic Issue Map** and toggle heatmap/filter controls.
11. Open **Unified Civic Issues** and inspect supporting report count/priority.
12. Verify the issue, assign it and change it to `IN_PROGRESS`.
13. Login back as the citizen and open the linked issue to see status history.
14. Mark the issue `RESOLVED` from the admin panel.
15. Confirm `resolved_at` and status history are populated.

## 21. Common errors and fixes

### `connection refused` to PostgreSQL
Start the PostgreSQL service and verify the `DATABASE_URL` host/port/user/password.

### `type "geography" does not exist`
Connect to the application database and run:

```sql
CREATE EXTENSION postgis;
```

### AI shows `UNAVAILABLE`
This is expected when `AI_MODE=real` but `AI_MODEL_PATH` is missing/unreadable. Use `AI_MODE=demo` or provide a real checkpoint.

### GPS denied
Browser permissions must allow location access. The UI also supports clicking the Leaflet map to choose a location.

### Upload rejected
Use JPG/JPEG/PNG within `MAX_UPLOAD_SIZE_MB`.

### Admin pages return 403 / redirect
Login with an `ADMIN` role. Citizen sessions are not authorized for admin pages or APIs.

## 22. Future extensions

- notification service
- municipal department integration
- mobile client
- advanced image embeddings
- learned severity estimation
- real-time event streaming
- historical trend forecasting
- municipal work-order integration
- route optimization for field teams

## 23. Academic limitations / honesty notes

This is a functional prototype architecture. The DEMO AI path is clearly labelled and must not be presented as a trained-model benchmark. Real AI performance, precision/recall, duplicate-detection effectiveness and governance impact require a separately trained/evaluated dataset and an empirical study.

## 24. Deploy on Vercel with Firebase Auth and Supabase Postgres

The app uses Firebase Authentication for email/password identities and Supabase Postgres (including PostGIS) for application data. The Flask app connects directly to the Supabase PostgreSQL session pooler through `DATABASE_URL`; the Supabase browser API key is not needed.

1. In Supabase, create or select a project, enable the `postgis` extension, and copy its **Session pooler** connection string. Use it as Vercel's `DATABASE_URL` with `sslmode=require`.
2. For a new Supabase database, run `database/schema.sql` and then `database/seed.sql` in the SQL Editor (the schema enables PostGIS and locks down the exposed API roles). For an existing Smart Civic database, apply `database/migrations/20261024_firebase_auth_identity.sql` and `database/migrations/20261024_supabase_api_lockdown.sql` before deployment.
3. In Firebase Console, enable **Authentication → Email/Password**. Add the eventual Vercel hostname under Authentication authorized domains so email verification links are accepted.
4. Configure Vercel environment variables for Production (and Preview if wanted): `DATABASE_URL`, a long random `SECRET_KEY`, `SESSION_COOKIE_SECURE=true`, `FIREBASE_WEB_API_KEY`, `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_JSON` (the complete Firebase Admin service-account JSON), and `FIREBASE_STORAGE_BUCKET`. Private Firebase Storage is used for report images and is required for report submissions on Vercel; images are served through an authenticated owner/admin route. Keep the service-account JSON and database password server-side; do not put them in frontend variables.
5. Deploy the GitHub repository to Vercel. Vercel skips `create_all` and seed writes at startup; the SQL setup above must be complete first. Existing admin records keep their role when their verified Firebase email is linked on first sign-in. Newly registered accounts are always citizens; grant admin roles only through trusted database administration.

Firebase email/password accounts must verify their email before the app creates or links the corresponding user row. Existing users must sign up or sign in through the same Firebase project with the email already stored in Smart Civic.
