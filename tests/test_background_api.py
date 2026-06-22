"""Tests for background job REST API."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_queue_stats_endpoint(client: TestClient) -> None:
    with patch("app.api.background_routes.get_queue_stats") as mock_stats:
        mock_stats.return_value = {"unified_queue": 2, "legacy_inspection_queue": 0, "total": 2}
        response = client.get("/api/background/queue")
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_enqueue_scan_api(client: TestClient) -> None:
    with patch("app.api.background_routes.create_and_enqueue_scan") as mock_create:
        mock_create.return_value = (42, 3)
        response = client.post(
            "/api/background/scans",
            json={"category": "dentist", "city": "Austin", "state": "TX"},
        )
    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == 42
    assert data["mode"] == "queued"
    assert data["queue_length"] == 3


def test_enqueue_inspection_api(client: TestClient) -> None:
    client.post(
        "/api/scans",
        json={"category": "cafe", "city": "QueueCity", "state": "FL", "limit": 3},
    )
    lead_id = client.get("/api/leads?city=QueueCity").json()["items"][0]["id"]
    with patch("app.api.background_routes.enqueue_inspection") as mock_enqueue:
        mock_enqueue.return_value = 1
        response = client.post(f"/api/background/inspections/leads/{lead_id}")
    assert response.status_code == 202
    assert response.json()["queued"] == 1


def test_schedules_list_api(client: TestClient) -> None:
    response = client.get("/api/background/schedules")
    assert response.status_code == 200
    assert "items" in response.json()


def test_create_schedule_api(client: TestClient) -> None:
    response = client.post(
        "/api/background/schedules",
        json={
            "name": "Nightly inspect",
            "task_type": "inspect_unreviewed",
            "interval_minutes": 120,
            "payload": {"uninspected_limit": 10},
        },
    )
    assert response.status_code == 201
    assert response.json()["task_type"] == "inspect_unreviewed"


def test_schedules_page(client: TestClient) -> None:
    response = client.get("/schedules")
    assert response.status_code == 200
    assert "Scheduled Tasks" in response.text
