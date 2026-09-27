from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_unknown_route_uses_standard_error_format(client: TestClient) -> None:
    response = client.get("/api/no-existe")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_404"
    assert response.json()["error"]["message"] == "Recurso no encontrado."
