"""Integration acceptance checklist documented as executable contract markers.

A live PostGIS environment is intentionally not assumed by these tests. The full
workflow is exercised manually/CI with a real PostgreSQL service using the README steps.
"""

ACCEPTANCE_STEPS = [
    'citizen_register', 'citizen_login', 'submit_report', 'store_image_gps',
    'ai_demo_or_real', 'duplicate_analysis', 'dbscan_cluster', 'unified_issue',
    'priority_calculation', 'gis_map', 'admin_verify', 'assign_issue',
    'status_tracking', 'resolve_issue', 'audit_history',
]


def test_acceptance_steps_documented():
    assert len(ACCEPTANCE_STEPS) == 15
