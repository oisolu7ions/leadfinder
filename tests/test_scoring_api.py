"""Tests for scoring API."""

from fastapi.testclient import TestClient


def test_api_score_lead(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "salon", "city": "Nashville", "state": "TN", "limit": 3},
    )
    leads = client.get("/api/leads?city=Nashville")
    lead_id = leads.json()["items"][0]["id"]

    response = client.post(f"/api/scoring/leads/{lead_id}")
    assert response.status_code == 200
    data = response.json()
    assert "total_score" in data
    assert data["breakdown"]["priority_tier"] in ("high", "medium", "low")

    get_score = client.get(f"/api/scoring/leads/{lead_id}")
    assert get_score.status_code == 200


def test_api_bulk_score_unscored(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "cafe", "city": "Boise", "state": "ID", "limit": 5},
    )
    response = client.post("/api/scoring/bulk/unscored?limit=10")
    assert response.status_code == 200
    assert response.json()["scored"] >= 1


def test_lead_detail_shows_score_breakdown(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "plumber", "city": "Raleigh", "state": "NC", "limit": 2},
    )
    lead_id = client.get("/api/leads?city=Raleigh").json()["items"][0]["id"]
    client.post(f"/api/scoring/leads/{lead_id}")

    page = client.get(f"/leads/{lead_id}")
    assert page.status_code == 200
    assert "Lead Score" in page.text
    assert "Score breakdown" in page.text or "Explanation" in page.text
