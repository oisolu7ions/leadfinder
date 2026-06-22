"""Dashboard integration tests."""

from fastapi.testclient import TestClient


def test_dashboard_pages_load(client: TestClient) -> None:
    for path in ("/", "/scans", "/leads", "/exports", "/inspections", "/schedules", "/settings", "/outreach"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_dashboard_home_content(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Lead Discovery Dashboard" in response.text
    assert "Needs Review Queue" in response.text
    assert "Run Scan" in response.text


def test_settings_page_content(client: TestClient) -> None:
    response = client.get("/settings")
    assert response.status_code == 200
    assert "Environment" in response.text
    assert "Browser inspection" in response.text
    assert "SECRET" not in response.text


def test_leads_list_page_content(client: TestClient) -> None:
    response = client.get("/leads")
    assert response.status_code == 200
    assert "Filters" in response.text
    assert "Score Unscored" in response.text


def test_inspections_page_content(client: TestClient) -> None:
    response = client.get("/inspections")
    assert response.status_code == 200
    assert "Inspect Unreviewed" in response.text
    assert "Reachable" in response.text


def test_scans_page_content(client: TestClient) -> None:
    response = client.get("/scans")
    assert response.status_code == 200
    assert "Run Scan" in response.text
    assert "Recent Scan Jobs" in response.text


def test_empty_dashboard_shows_scan_cta(client: TestClient) -> None:
    response = client.get("/")
    if "No leads yet" in response.text:
        assert "Run First Scan" in response.text


def test_run_scan_via_form(client: TestClient) -> None:
    scans = client.get("/scans")
    csrf = _extract_csrf(scans.text)
    response = client.post(
        "/scans/run",
        data={
            "csrf_token": csrf,
            "category": "dentist",
            "city": "Phoenix",
            "state": "AZ",
            "source_name": "mock",
            "mode": "sync",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    leads = client.get("/leads?city=Phoenix")
    assert leads.status_code == 200
    assert "Phoenix" in leads.text


def test_lead_detail_and_inspection_flow(client: TestClient) -> None:
    from unittest.mock import MagicMock, patch

    from app.services.inspection_heuristics import HttpFetchResult

    _run_sample_scan(client)
    leads = client.get("/leads?city=Denver")
    assert "Denver" in leads.text
    lead_id = _first_lead_id(leads.text)
    assert lead_id is not None

    detail = client.get(f"/leads/{lead_id}")
    assert detail.status_code == 200
    assert "Lead Score" in detail.text
    assert "Website Findings Summary" in detail.text
    csrf = _extract_csrf(detail.text)

    mock_fetcher = MagicMock(
        fetch=MagicMock(
            return_value=HttpFetchResult(
                final_url="https://mock.test/",
                http_status=200,
                reachable=True,
                ssl_present=True,
                html="<html><head><title>Denver Test</title></head><body></body></html>",
            )
        )
    )
    with patch("app.services.inspection_service.HttpxFetcher", return_value=mock_fetcher):
        inspected = client.post(
            f"/leads/{lead_id}/inspect",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
    assert inspected.status_code == 303

    after = client.get(f"/leads/{lead_id}")
    assert "Website Findings Summary" in after.text
    assert "Denver Test" in after.text or "Reachable" in after.text


def _run_sample_scan(client: TestClient) -> None:
    page = client.get("/scans")
    csrf = _extract_csrf(page.text)
    client.post(
        "/scans/run",
        data={
            "csrf_token": csrf,
            "category": "plumber",
            "city": "Denver",
            "state": "CO",
            "source_name": "mock",
            "mode": "sync",
        },
        follow_redirects=True,
    )


def _extract_csrf(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return html[start:end]


def _first_lead_id(html: str) -> int | None:
    marker = 'href="/leads/'
    if marker not in html:
        return None
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return int(html[start:end])
