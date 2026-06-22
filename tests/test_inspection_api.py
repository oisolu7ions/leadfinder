"""Tests for inspection API and queue."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.services.inspection_heuristics import HttpFetchResult
from app.services.inspection_queue import enqueue_inspection, get_queue_length
from app.services.scan import create_scan_job, ensure_default_sources, run_scan_job


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def _mock_fetcher():
    return MagicMock(
        fetch=MagicMock(
            return_value=HttpFetchResult(
                final_url="https://mock.test/",
                http_status=200,
                reachable=True,
                ssl_present=True,
                html="<html><head><title>Mock</title></head><body></body></html>",
            )
        )
    )


def test_api_inspect_lead(client: TestClient) -> None:
    _run_scan(client, "Tampa")
    lead_id = _first_lead_id(client, "Tampa")
    with patch("app.services.inspection_service.HttpxFetcher", return_value=_mock_fetcher()):
        response = client.post(f"/api/inspections/leads/{lead_id}", json={"auto_score": False})
    assert response.status_code == 200
    data = response.json()
    assert data["business_lead_id"] == lead_id
    assert data["findings"] is not None


def test_api_queue_inspection(client: TestClient) -> None:
    _run_scan(client, "Orlando")
    lead_id = _first_lead_id(client, "Orlando")
    with patch("app.workers.queue.get_redis_client") as mock_redis:
        mock_client = MagicMock()
        mock_client.rpush.return_value = 1
        mock_client.llen.return_value = 1
        mock_redis.return_value = mock_client
        response = client.post(f"/api/inspections/leads/{lead_id}/queue")
    assert response.status_code == 200
    assert response.json()["queued"] == 1


def test_inspections_page(client: TestClient) -> None:
    response = client.get("/inspections")
    assert response.status_code == 200
    assert "Inspections" in response.text


def test_queue_module_with_mock_redis() -> None:
    mock_client = MagicMock()
    mock_client.rpush.return_value = 2
    mock_client.llen.return_value = 2
    with patch("app.workers.queue.get_redis_client", return_value=mock_client):
        length = enqueue_inspection(99)
    assert length == 2
    mock_client.llen.side_effect = [2, 0]
    with patch("app.workers.queue.get_redis_client", return_value=mock_client):
        assert get_queue_length() == 2


def _run_scan(client: TestClient, city: str) -> None:
    client.post(
        "/api/scans",
        json={"category": "cafe", "city": city, "state": "FL", "limit": 5},
    )


def _first_lead_id(client: TestClient, city: str) -> int:
    response = client.get(f"/api/leads?city={city}")
    return response.json()["items"][0]["id"]
