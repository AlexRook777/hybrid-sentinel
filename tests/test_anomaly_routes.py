"""Tests for anomaly routes."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hybrid_sentinel.anomaly.scorer import AnomalyScorer
from hybrid_sentinel.main import app


@pytest.fixture
def scorer_client():
    """Create test client with a mocked scorer available."""
    scorer = AnomalyScorer()
    with patch("hybrid_sentinel.anomaly._scorer", scorer):
        yield TestClient(app), scorer


def test_anomaly_stats_endpoint_returns_stats(scorer_client):
    """GET /anomalies/stats returns scorer statistics."""
    client, _ = scorer_client
    response = client.get("/anomalies/stats")

    assert response.status_code == 200
    data = response.json()

    # Check expected keys
    assert "is_warmed_up" in data
    assert "events_processed" in data
    assert "warmup_target" in data
    assert "anomalies_emitted" in data
    assert "drift_detectors_active" in data

    # Check types
    assert isinstance(data["is_warmed_up"], bool)
    assert isinstance(data["events_processed"], int)
    assert isinstance(data["warmup_target"], int)
    assert isinstance(data["anomalies_emitted"], int)
    assert isinstance(data["drift_detectors_active"], int)


def test_anomaly_stats_warmup_state(scorer_client):
    """Verify stats reflect warmup state correctly."""
    client, _ = scorer_client
    response = client.get("/anomalies/stats")
    assert response.status_code == 200
    data = response.json()

    # Fresh scorer should not be warmed up
    assert data["is_warmed_up"] is False
    assert data["events_processed"] == 0
    assert data["warmup_target"] == 1000


def test_anomaly_stats_503_when_scorer_not_running():
    """GET /anomalies/stats returns 503 when scorer is not running."""
    with patch("hybrid_sentinel.anomaly._scorer", None):
        client = TestClient(app)
        response = client.get("/anomalies/stats")
        assert response.status_code == 503
