"""Tests for health and liveness endpoints."""

from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_endpoint_shape(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "leadfinder"
    assert "version" in data
    assert data["database"] in ("ok", "error")
    assert data["redis"] in ("ok", "error")
    assert data["status"] in ("ok", "degraded")


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] in ("ready", "not_ready")


def test_dashboard_home(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Lead Discovery Dashboard" in response.text
    assert "Recent Scan Jobs" in response.text
    assert "Needs Review Queue" in response.text
