CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    firebase_uid VARCHAR(128) UNIQUE,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mobile VARCHAR(30) NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(20) NOT NULL CHECK (role IN ('CITIZEN','ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS issue_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL,
    slug VARCHAR(80) UNIQUE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER NOT NULL REFERENCES issue_categories(id),
    description TEXT NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    location_geometry GEOGRAPHY(POINT,4326) NOT NULL,
    submission_status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
    self_reported_severity INTEGER NOT NULL DEFAULT 3 CHECK (self_reported_severity BETWEEN 1 AND 5),
    -- Multilingual fields
    original_text TEXT,
    translated_text TEXT,
    detected_language VARCHAR(10) DEFAULT 'en',
    selected_language VARCHAR(10) DEFAULT 'en',
    recommended_department VARCHAR(100),
    suggested_action TEXT,
    -- Geotag / EXIF GPS verification
    -- Status: VERIFIED | MISMATCH | NO_EXIF_GPS | EXTRACTION_ERROR | PENDING
    geotag_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    geotag_lat DOUBLE PRECISION,
    geotag_lon DOUBLE PRECISION,
    geotag_altitude DOUBLE PRECISION,
    geotag_distance_m DOUBLE PRECISION,
    geotag_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_location_gist ON reports USING GIST(location_geometry);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_category ON reports(category_id);
CREATE INDEX IF NOT EXISTS idx_reports_geotag_status ON reports(geotag_status);


CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    issue_code VARCHAR(30) UNIQUE NOT NULL,
    category_id INTEGER NOT NULL REFERENCES issue_categories(id),
    description TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_geometry GEOGRAPHY(POINT,4326) NOT NULL,
    severity INTEGER NOT NULL DEFAULT 3 CHECK (severity BETWEEN 1 AND 5),
    severity_source VARCHAR(20) NOT NULL DEFAULT 'CITIZEN',
    report_count INTEGER NOT NULL DEFAULT 1,
    age_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    location_importance INTEGER NOT NULL DEFAULT 1 CHECK (location_importance BETWEEN 1 AND 5),
    priority_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    priority_level VARCHAR(10) NOT NULL DEFAULT 'LOW',
    status VARCHAR(30) NOT NULL DEFAULT 'REPORTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_issues_location_gist ON issues USING GIST(location_geometry);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues(priority_level);

CREATE TABLE IF NOT EXISTS issue_reports (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    report_id INTEGER UNIQUE NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    link_method VARCHAR(30) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_issue_reports_issue ON issue_reports(issue_id);

CREATE TABLE IF NOT EXISTS ai_detections (
    id SERIAL PRIMARY KEY,
    report_id INTEGER UNIQUE NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    detected_category VARCHAR(80),
    confidence_score DOUBLE PRECISION,
    bounding_box JSONB,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_time_ms DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id SERIAL PRIMARY KEY,
    new_report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    existing_report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    distance_meters DOUBLE PRECISION NOT NULL,
    category_similarity DOUBLE PRECISION NOT NULL,
    image_similarity DOUBLE PRECISION NOT NULL,
    text_similarity DOUBLE PRECISION NOT NULL,
    overall_similarity DOUBLE PRECISION NOT NULL,
    decision VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_duplicate_decision ON duplicate_candidates(decision);
CREATE INDEX IF NOT EXISTS idx_duplicate_score ON duplicate_candidates(overall_similarity);

CREATE TABLE IF NOT EXISTS issue_status_history (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    remarks TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_status_history_issue ON issue_status_history(issue_id);

CREATE TABLE IF NOT EXISTS issue_assignments (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    assigned_to VARCHAR(120) NOT NULL,
    department VARCHAR(120) NOT NULL,
    remarks TEXT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(120) UNIQUE NOT NULL,
    setting_value VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The Flask API connects directly as the database owner. Keep the public
-- Supabase Data API roles from reaching civic reports and user profile data.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE users, issue_categories, reports, issues, issue_reports,
    ai_detections, duplicate_candidates, issue_status_history,
    issue_assignments, system_settings FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated;
