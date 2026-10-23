"""End-to-end test for the report -> AI -> duplicate -> clustering -> issue -> admin status path.

Run against an isolated PostgreSQL/PostGIS database only:

PowerShell:
    $env:RUN_POSTGIS_TESTS='1'
    $env:TEST_DATABASE_URL='postgresql+psycopg2://...'
    pytest -q tests/test_integration_postgis.py
"""
import io
import os

import pytest
from PIL import Image

from app import create_app, db
from app.models import User, IssueCategory
from app.utils.security import hash_password


pytestmark = pytest.mark.integration


def _csrf(client):
    client.get('/login')
    with client.session_transaction() as sess:
        return sess['csrf_token']


@pytest.fixture()
def postgis_app():
    if os.getenv('RUN_POSTGIS_TESTS') != '1':
        pytest.skip('Set RUN_POSTGIS_TESTS=1 to run the PostGIS integration test.')
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL is required for the PostGIS integration test.')
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': url, 'UPLOAD_FOLDER': os.path.join(os.getcwd(), 'uploads', 'test'), 'AI_MODE': 'demo'})
    with app.app_context():
        db.drop_all()
        db.create_all()
        from app.services.seed_service import ensure_seed_categories_and_settings
        ensure_seed_categories_and_settings()
        db.session.add(User(name='Admin', email='admin-test@example.com', mobile='9000000000', password_hash=hash_password('Admin@12345'), role='ADMIN'))
        db.session.add(User(name='Citizen', email='citizen-test@example.com', mobile='9000000001', password_hash=hash_password('Citizen@12345'), role='CITIZEN'))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _login(client, email, password):
    token = _csrf(client)
    response = client.post('/api/auth/login', json={'email': email, 'password': password}, headers={'X-CSRF-Token': token})
    assert response.status_code == 200
    return client


def _image_bytes():
    im = Image.new('RGB', (160, 120), (80, 80, 80))
    buf = io.BytesIO()
    im.save(buf, format='JPEG')
    buf.seek(0)
    return buf


def test_complete_postgis_report_to_resolution_workflow(postgis_app):
    citizen = postgis_app.test_client()
    _login(citizen, 'citizen-test@example.com', 'Citizen@12345')
    with postgis_app.app_context():
        category = IssueCategory.query.filter_by(slug='pothole').first()
        category_id = category.id

    image = _image_bytes()
    response = citizen.post('/api/reports', data={'category_id': str(category_id), 'description': 'Large pothole near college gate', 'latitude': '18.5208', 'longitude': '73.8567', 'severity': '5', 'image': (image, 'pothole.jpg')}, content_type='multipart/form-data')
    assert response.status_code == 201
    data = response.get_json()['data']
    assert data['id'] and data['ai']['status'] in {'DEMO_DETECTED', 'UNAVAILABLE', 'MANUAL_REVIEW'}
    assert data['issue_id'] is not None

    # Second nearby report creates a duplicate candidate and remains linkable to the cluster.
    image2 = _image_bytes()
    response2 = citizen.post('/api/reports', data={'category_id': str(category_id), 'description': 'Big pothole at college entrance', 'latitude': '18.52085', 'longitude': '73.85672', 'severity': '4', 'image': (image2, 'pothole2.jpg')}, content_type='multipart/form-data')
    assert response2.status_code == 201
    assert response2.get_json()['data']['issue_id'] is not None

    admin = postgis_app.test_client()
    _login(admin, 'admin-test@example.com', 'Admin@12345')
    report_list = admin.get('/api/admin/reports?page=1&limit=20')
    assert report_list.status_code == 200
    issues = admin.get('/api/admin/issues?page=1&limit=20')
    assert issues.status_code == 200 and issues.get_json()['data']
    issue_id = issues.get_json()['data'][0]['id']

    verify = admin.post(f'/api/admin/issues/{issue_id}/verify', headers={'X-CSRF-Token': _csrf(admin)})
    assert verify.status_code == 200
    status = admin.post(f'/api/admin/issues/{issue_id}/status', json={'status':'IN_PROGRESS','remarks':'Integration test assignment'}, headers={'X-CSRF-Token': _csrf(admin)})
    assert status.status_code == 200
    resolve = admin.post(f'/api/admin/issues/{issue_id}/status', json={'status':'RESOLVED','remarks':'Integration test resolution'}, headers={'X-CSRF-Token': _csrf(admin)})
    assert resolve.status_code == 200

    detail = citizen.get(f'/api/issues/{issue_id}')
    assert detail.status_code == 200
    assert detail.get_json()['data']['status'] == 'RESOLVED'
    assert detail.get_json()['data']['status_history']
