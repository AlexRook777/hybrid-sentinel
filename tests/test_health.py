"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from hybrid_sentinel import __version__


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["status"] == "ok"


def test_health_includes_version(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["version"] == __version__
