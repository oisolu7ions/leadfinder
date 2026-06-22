"""Tests for export API and dashboard."""

import csv
import io

from fastapi.testclient import TestClient


def test_api_create_and_download_export(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "dentist", "city": "Columbus", "state": "OH", "limit": 3},
    )
    response = client.post(
        "/api/exports",
        json={"format": "csv", "filters": {"city": "Columbus"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["row_count"] >= 1

    download = client.get(f"/api/exports/{data['id']}/download")
    assert download.status_code == 200
    assert "text/csv" in download.headers.get("content-type", "")

    reader = csv.DictReader(io.StringIO(download.text))
    rows = list(reader)
    assert len(rows) >= 1
    assert "business_name" in rows[0]
    assert "total_score" in rows[0]


def test_api_list_exports(client: TestClient) -> None:
    client.post("/api/exports", json={"filters": {"city": "Nowhere"}})
    response = client.get("/api/exports")
    assert response.status_code == 200
    assert "items" in response.json()


def test_exports_page_renders(client: TestClient) -> None:
    response = client.get("/exports")
    assert response.status_code == 200
    assert "Create Export" in response.text
    assert "Export History" in response.text


def test_leads_export_current_view(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "cafe", "city": "Savannah", "state": "GA", "limit": 2},
    )
    leads_page = client.get("/leads?city=Savannah")
    csrf = _extract_csrf(leads_page.text)
    response = client.post(
        "/leads/export",
        data={"csrf_token": csrf, "city": "Savannah"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/exports/" in response.headers["location"]


def _extract_csrf(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return html[start:end]
