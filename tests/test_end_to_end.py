"""End-to-end integration tests for the anomaly investigation agent."""

import time
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import hybrid_sentinel.stream.sink as sink
from hybrid_sentinel.agent import investigation_bus, start_agent, stop_agent
from hybrid_sentinel.agent.store import clear_cases
from hybrid_sentinel.anomaly.scorer import AnomalyScorer
from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import EventBus
from hybrid_sentinel.main import app
from hybrid_sentinel.models import AnomalyEvent

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    investigation_bus.reset()
    clear_cases()
    sink.matched_pairs.clear()
    settings.agent_enabled = True
    settings.agent_llm_model = "mock"
    yield
    stop_agent()
    investigation_bus.reset()
    clear_cases()
    sink.matched_pairs.clear()


def test_end_to_end_investigation_flow():
    """Test full flow: Anomaly Scorer -> Investigation Bus -> Agent -> API."""
    start_agent()

    scoring_bus = EventBus()
    scorer = AnomalyScorer()
    scorer._is_warmed_up = True
    scorer._model.score_one = lambda x: 1.0

    scorer.start(scoring_bus)

    try:
        timeout_event = AnomalyEvent(
            anomaly_type="TIMEOUT",
            merchant_id="e2e-merchant",
            transaction_id="tx-e2e",
            provider_id="p-e2e",
            timestamp=datetime.now(UTC),
            details={},
        )
        scoring_bus.enqueue(timeout_event)

        time.sleep(1.0)

        response = client.get("/cases")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        case = data[0]
        assert case["anomaly_event"]["merchant_id"] == "e2e-merchant"
        assert case["pattern"] == "behavioral"
        assert case["severity"] == "MEDIUM"
        assert "recommendation" in case

    finally:
        scorer.stop()
        scoring_bus.stop()


def test_agent_disabled_integration():
    """Test full system when agent is disabled via config."""
    settings.agent_enabled = False
    start_agent()

    scoring_bus = EventBus()
    scorer = AnomalyScorer()
    scorer._is_warmed_up = True
    scorer._model.score_one = lambda x: 1.0

    scorer.start(scoring_bus)

    try:
        timeout_event = AnomalyEvent(
            anomaly_type="TIMEOUT",
            merchant_id="e2e-merchant-disabled",
            transaction_id="tx-e2e",
            provider_id="p-e2e",
            timestamp=datetime.now(UTC),
            details={},
        )
        scoring_bus.enqueue(timeout_event)

        time.sleep(0.5)

        # Bus has size=1 when agent disabled; event may or may not fit
        # The key assertion is that no cases are produced
        response = client.get("/cases")
        assert response.status_code == 200
        assert len(response.json()) == 0

    finally:
        scorer.stop()
        scoring_bus.stop()
