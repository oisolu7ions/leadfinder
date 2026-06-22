"""Tests for outreach API and dashboard rendering."""

from fastapi.testclient import TestClient


def test_api_generate_draft(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "cafe", "city": "Madison", "state": "WI", "limit": 3},
    )
    lead_id = client.get("/api/leads?city=Madison").json()["items"][0]["id"]

    response = client.post(f"/api/outreach/leads/{lead_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["draft"]["subject_line"]
    assert data["draft"]["primary_angle"]
    assert "not sent" in data["message"].lower()

    latest = client.get(f"/api/outreach/leads/{lead_id}/latest")
    assert latest.status_code == 200


def test_api_regenerate_draft(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "barber", "city": "Tampa", "state": "FL", "limit": 2},
    )
    lead_id = client.get("/api/leads?city=Tampa").json()["items"][0]["id"]
    first = client.post(f"/api/outreach/leads/{lead_id}").json()["draft"]["id"]
    second = client.post(f"/api/outreach/leads/{lead_id}/regenerate").json()["draft"]["id"]
    assert second != first


def test_api_mark_reviewed(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "spa", "city": "Eugene", "state": "OR", "limit": 2},
    )
    lead_id = client.get("/api/leads?city=Eugene").json()["items"][0]["id"]
    draft_id = client.post(f"/api/outreach/leads/{lead_id}").json()["draft"]["id"]
    response = client.post(f"/api/outreach/drafts/{draft_id}/reviewed")
    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"


def test_outreach_list_page(client: TestClient) -> None:
    response = client.get("/outreach")
    assert response.status_code == 200
    assert "Outreach Drafts" in response.text


def test_lead_detail_shows_draft(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "gym", "city": "Spokane", "state": "WA", "limit": 2},
    )
    lead_id = client.get("/api/leads?city=Spokane").json()["items"][0]["id"]
    client.post(f"/api/outreach/leads/{lead_id}")

    page = client.get(f"/leads/{lead_id}")
    assert page.status_code == 200
    assert "Outreach Draft" in page.text
    assert "Why this angle" in page.text
    assert "Call notes" in page.text
