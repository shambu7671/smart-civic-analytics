"""
Database migration script — applies any schema changes that were added to
SQLAlchemy models after the initial schema.sql was created.

Run before starting the app in production:
    python scripts/migrate.py

Also used as the Heroku/Railway release command via Procfile:
    release: python scripts/migrate.py
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text, inspect


MIGRATIONS = [
    # ── v1.1: Geotag / EXIF GPS verification columns ─────────────────────────
    {
        "id": "001_geotag_columns",
        "description": "Add EXIF GPS geotag verification columns to reports table",
        "sql": [
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_status   VARCHAR(30) NOT NULL DEFAULT 'PENDING'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_lat       DOUBLE PRECISION",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_lon       DOUBLE PRECISION",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_altitude  DOUBLE PRECISION",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_distance_m DOUBLE PRECISION",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geotag_message   TEXT",
            "CREATE INDEX IF NOT EXISTS ix_reports_geotag_status ON reports (geotag_status)",
        ],
    },
    # ── v1.2: Translation / multilingual columns ──────────────────────────────
    {
        "id": "002_translation_columns",
        "description": "Add multilingual translation columns to reports table",
        "sql": [
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS original_text          TEXT",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS translated_text        TEXT",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS detected_language      VARCHAR(10) DEFAULT 'en'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS selected_language      VARCHAR(10) DEFAULT 'en'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS recommended_department VARCHAR(100)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS suggested_action       TEXT",
        ],
    },
    # ── v1.3: Ensure PostGIS extension is enabled ─────────────────────────────
    {
        "id": "003_postgis_extension",
        "description": "Enable PostGIS extension if not already present",
        "sql": [
            "CREATE EXTENSION IF NOT EXISTS postgis",
        ],
    },
]


def run_migrations():
    app = create_app()
    with app.app_context():
        # Ensure migrations tracking table exists
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS _schema_migrations (
                id          VARCHAR(60) PRIMARY KEY,
                description TEXT,
                applied_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        db.session.commit()

        applied = {
            row[0]
            for row in db.session.execute(text("SELECT id FROM _schema_migrations")).fetchall()
        }

        ran = 0
        for migration in MIGRATIONS:
            if migration["id"] in applied:
                print(f"  [skip]  {migration['id']}: {migration['description']}")
                continue

            print(f"  [apply] {migration['id']}: {migration['description']}")
            try:
                for sql in migration["sql"]:
                    db.session.execute(text(sql))
                db.session.execute(
                    text("INSERT INTO _schema_migrations (id, description) VALUES (:id, :desc)"),
                    {"id": migration["id"], "desc": migration["description"]},
                )
                db.session.commit()
                ran += 1
                print(f"          -> OK")
            except Exception as exc:
                db.session.rollback()
                print(f"          -> ERROR: {exc}")
                sys.exit(1)

        # Always run db.create_all() to create any missing tables
        db.create_all()
        print(f"\nMigrations complete. {ran} new migration(s) applied.")


if __name__ == "__main__":
    print("=== Smart Civic System — Schema Migration ===\n")
    run_migrations()
