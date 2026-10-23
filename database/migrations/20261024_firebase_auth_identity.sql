-- Apply once to an existing Smart Civic PostgreSQL database when switching
-- authentication from local password hashes to Firebase Authentication.
ALTER TABLE users ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_firebase_uid ON users (firebase_uid);
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
