"""Tests for anomaly scorer integration with the investigation bus."""

import time
from datetime import UTC, datetime

import pytest

from hybrid_sentinel.agent import investigation_bus
from hybrid_sentinel.anomaly.scorer import AnomalyScorer
from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import EventBus
from hybrid_sentinel.models import AnomalyEvent


@pytest.fixture()
def clean_buses():
    """Reset the investigation bus and return a fresh scoring bus."""
    investigation_bus.reset()
    scoring_bus = EventBus()
    yield scoring_bus
    investigation_bus.reset()
    scoring_bus.stop()


def test_scorer_publishes_to_investigation_bus(clean_buses):
    """Test that scored anomalies are published to the investigation bus."""
    scoring_bus = clean_buses
    scorer = AnomalyScorer()

    # Bypass warmup and force score > threshold
    scorer._is_warmed_up = True
    scorer._model.score_one = lambda x: 1.0

    scorer.start(scoring_bus)

    try:
        timeout_event = AnomalyEvent(
            anomaly_type="TIMEOUT",
            merchant_id="m1",
            transaction_id="tx1",
            provider_id="p1",
            timestamp=datetime.now(UTC),
            details={},
            anomaly_score=0.0,
        )

        scoring_bus.enqueue(timeout_event)
        time.sleep(0.5)

        investigated = investigation_bus.dequeue_nowait()
        assert investigated is not None
        assert investigated.merchant_id == "m1"
        assert investigated.anomaly_type == "TIMEOUT"
    finally:
        scorer.stop()


def test_investigation_bus_backpressure():
    """Test that a full investigation bus does not crash the scorer."""
    scorer = AnomalyScorer()
    scorer._is_warmed_up = True
    scorer._model.score_one = lambda x: 1.0

    # Fill the investigation bus
    max_size = settings.investigation_queue_max_size
    for i in range(max_size):
        investigation_bus.enqueue(
            AnomalyEvent(
                anomaly_type="TIMEOUT",
                merchant_id=f"m{i}",
                transaction_id=f"tx{i}",
                provider_id="p",
                timestamp=datetime.now(UTC),
            )
        )

    assert investigation_bus.is_full()

    # Now score a new event — should not block or crash
    timeout_event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="m999",
        transaction_id="tx999",
        provider_id="p1",
        timestamp=datetime.now(UTC),
    )

    scorer.score_event(timeout_event)

    # Internal list updated but bus dropped the event (non-blocking)
    scored = scorer.get_scored_anomalies()
    assert len(scored) == 1
    assert scored[0].merchant_id == "m999"

    investigation_bus.reset()

