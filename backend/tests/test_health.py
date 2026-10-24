def test_health(api_client):
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_csrf_endpoint_sets_cookie(api_client):
    response = api_client.get("/api/v1/csrf/")
    assert response.status_code == 204
    assert "csrftoken" in response.cookies


def test_openapi_schema_is_generated(api_client, db):
    response = api_client.get("/api/schema/")
    assert response.status_code == 200
