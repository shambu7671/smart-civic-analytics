-- Base seed for categories and system settings.
-- For secure passwords + 10 citizens + 20 reports + 8 issues, run:
--     python scripts/seed_demo.py

INSERT INTO issue_categories (name, slug, active, description) VALUES
('Pothole','pothole',TRUE,'Surface depression or hole affecting road safety.'),
('Road Damage','road-damage',TRUE,'Major road surface damage beyond a single crack/pothole.'),
('Road Crack','road-crack',TRUE,'Visible cracking in the road surface.'),
('Other / Manual Review','manual-review',TRUE,'Issue requiring manual categorisation.')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('DUPLICATE_RADIUS_METERS','100','Nearby search radius used for duplicate candidates.'),
('DUPLICATE_CANDIDATE_THRESHOLD','0.45','Minimum overall similarity for creating a duplicate candidate.'),
('DUPLICATE_LOCATION_WEIGHT','0.30','Duplicate score weight for geographic proximity.'),
('DUPLICATE_CATEGORY_WEIGHT','0.20','Duplicate score weight for category match.'),
('DUPLICATE_IMAGE_WEIGHT','0.30','Duplicate score weight for image similarity.'),
('DUPLICATE_TEXT_WEIGHT','0.20','Duplicate score weight for text similarity.'),
('IMAGE_SIMILARITY_THRESHOLD','0.65','Explainable image similarity threshold.'),
('TEXT_SIMILARITY_THRESHOLD','0.35','TF-IDF cosine similarity threshold.'),
('DBSCAN_EPS_METERS','80','DBSCAN epsilon in meters.'),
('DBSCAN_MIN_SAMPLES','2','DBSCAN minimum samples.'),
('SEVERITY_WEIGHT','0.35','Priority weight for severity.'),
('REPORT_WEIGHT','0.25','Priority weight for supporting report count.'),
('AGE_WEIGHT','0.20','Priority weight for issue age.'),
('LOCATION_WEIGHT','0.20','Priority weight for location importance.'),
('HIGH_PRIORITY_THRESHOLD','70','Score at or above this value is HIGH.'),
('MEDIUM_PRIORITY_THRESHOLD','45','Score at or above this value and below HIGH is MEDIUM.')
ON CONFLICT (setting_key) DO NOTHING;
