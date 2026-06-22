"""Tests for ingestion REST API."""

from fastapi.testclient import TestClient


def test_api_create_and_list_scan(client: TestClient) -> None:
    response = client.post(
        "/api/scans",
        json={
            "category": "plumber",
            "city": "Seattle",
            "state": "WA",
            "source_name": "mock",
            "limit": 10,
            "run_immediately": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_inserted"] + data["total_updated"] >= 1

    listing = client.get("/api/scans")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = client.get(f"/api/scans/{data['id']}")
    assert detail.status_code == 200
    assert detail.json()["city"] == "Seattle"


def test_api_create_scan_without_run(client: TestClient) -> None:
    created = client.post(
        "/api/scans",
        json={
            "category": "cafe",
            "city": "Portland",
            "state": "OR",
            "run_immediately": False,
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    ran = client.post(f"/api/scans/{job_id}/run?limit=5")
    assert ran.status_code == 200
    assert ran.json()["status"] == "completed"


def test_api_list_leads(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "salon", "city": "Miami", "state": "FL", "limit": 5},
    )
    response = client.get("/api/leads?city=Miami")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["city"] == "Miami"
