"""Tests for investigation cases API endpoints."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from hybrid_sentinel.agent.store import add_case, clear_cases
from hybrid_sentinel.main import app
from hybrid_sentinel.models import AnomalyEvent, CaseReport

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    clear_cases()
    yield
    clear_cases()


def create_mock_case(case_id: str) -> CaseReport:
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="m1",
        transaction_id="tx1",
        provider_id="p1",
        timestamp=datetime.now(UTC),
        anomaly_score=0.9,
    )
    return CaseReport(
        case_id=case_id,
        anomaly_event=event,
        severity="LOW",
        pattern="behavioral",
        merchant_failure_rate=0.0,
        merchant_avg_latency=0.0,
        merchant_event_count=0,
        provider_failure_rate=0.0,
        provider_affected_merchants=0,
        recommendation="mock",
        investigation_duration_ms=10,
        timestamp=datetime.now(UTC),
    )


def test_list_cases_empty():
    response = client.get("/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_list_cases():
    add_case(create_mock_case("case-1"))
    add_case(create_mock_case("case-2"))

    response = client.get("/cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["case_id"] == "case-2"  # LIFO order
    assert data[1]["case_id"] == "case-1"


def test_get_case():
    add_case(create_mock_case("case-123"))

    response = client.get("/cases/case-123")
    assert response.status_code == 200
    assert response.json()["case_id"] == "case-123"


def test_get_case_not_found():
    response = client.get("/cases/case-999")
    assert response.status_code == 404


def test_get_stats():
    add_case(create_mock_case("case-1"))
    add_case(create_mock_case("case-2"))

    response = client.get("/cases/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_investigations"] == 2
    assert data["cases_by_severity"]["LOW"] == 2
    assert data["cases_by_pattern"]["behavioral"] == 2
    assert data["agent_enabled"] is True
