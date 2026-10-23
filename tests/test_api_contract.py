from app import create_app


def test_public_pages_render_without_database_initialization():
    app = create_app({"TESTING": True, "SKIP_DB_INIT": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert client.get('/about').status_code == 200
    assert client.get('/contact').status_code == 200
    assert client.get('/login').status_code == 200
    assert client.get('/register').status_code == 200


def test_protected_admin_page_does_not_open_to_anonymous_user():
    app = create_app({"TESTING": True, "SKIP_DB_INIT": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = app.test_client()
    response = client.get('/admin/dashboard')
    assert response.status_code in (302, 401)


def test_health_check_endpoint():
    app = create_app({"TESTING": True, "SKIP_DB_INIT": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = app.test_client()
    res = client.get('/health')
    assert res.status_code in (200, 503)
    data = res.get_json()
    assert "status" in data
    assert "timestamp" in data

    res_api = client.get('/api/health')
    assert res_api.status_code in (200, 503)
