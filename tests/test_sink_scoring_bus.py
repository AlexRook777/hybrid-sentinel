"""Tests for sink's scoring bus integration."""

import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hybrid_sentinel.anomaly import get_scorer, scoring_bus, stop_scorer
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import CallbackEvent, TransactionEvent
from hybrid_sentinel.stream.sink import anomaly_events, matched_pairs


@pytest.mark.integration
def test_matched_pair_published_to_scoring_bus(stream_pipeline: None) -> None:
    """Verify MatchedPair is published to scoring bus and consumed by scorer."""
    scorer = get_scorer()
    assert scorer is not None, "Scorer should be running"

    initial_processed = scorer.get_stats()["events_processed"]

    txn = TransactionEvent(
        merchant_id="M_SCORE_1",
        transaction_id="T_SCORE_1",
        amount=Decimal("50.00"),
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_SCORE_1",
        transaction_id="T_SCORE_1",
        status="success",
        actual_amount=Decimal("50.00"),
        actual_currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for matched pair to appear in sink (proves Bytewax processed it)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(p.transaction.transaction_id == "T_SCORE_1" for p in matched_pairs):
            break
        time.sleep(0.2)

    assert any(
        p.transaction.transaction_id == "T_SCORE_1" for p in matched_pairs
    ), "MatchedPair not found in sink"

    # Wait for scorer to process it (proves sink → scoring bus → scorer path works)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if scorer.get_stats()["events_processed"] > initial_processed:
            break
        time.sleep(0.2)

    assert scorer.get_stats()["events_processed"] > initial_processed, (
        "Scorer did not process event from scoring bus"
    )


@pytest.mark.integration
def test_timeout_anomaly_published_to_scoring_bus(stream_pipeline: None) -> None:
    """Verify TIMEOUT AnomalyEvent is published to scoring bus and consumed by scorer."""
    scorer = get_scorer()
    assert scorer is not None

    initial_processed = scorer.get_stats()["events_processed"]

    txn = TransactionEvent(
        merchant_id="M_TIMEOUT_1",
        transaction_id="T_TIMEOUT_1",
        amount=Decimal("200.00"),
        currency="USD",
        provider_id="P2",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)

    # Wait for timeout (configured as 2s in test fixture)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(a.transaction_id == "T_TIMEOUT_1" for a in anomaly_events):
            break
        time.sleep(0.2)

    assert any(
        a.transaction_id == "T_TIMEOUT_1" for a in anomaly_events
    ), "TIMEOUT AnomalyEvent not found in sink"

    # Wait for scorer to process it (proves sink → scoring bus → scorer path works)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if scorer.get_stats()["events_processed"] > initial_processed:
            break
        time.sleep(0.2)

    assert scorer.get_stats()["events_processed"] > initial_processed, (
        "Scorer did not process TIMEOUT event from scoring bus"
    )


@pytest.mark.integration
def test_scoring_bus_full_does_not_block_stream(stream_pipeline: None) -> None:
    """Verify that a full scoring bus does not block Bytewax stream processing."""
    from hybrid_sentinel.config import settings

    # Stop the scorer so it doesn't drain the bus while we fill it
    stop_scorer()

    # Fill the scoring bus completely
    for _ in range(settings.scoring_queue_max_size):
        scoring_bus.enqueue("dummy")

    assert scoring_bus.is_full(), "Scoring bus should be full"

    # Submit transaction + callback — stream should NOT block
    txn = TransactionEvent(
        merchant_id="M_FULL_1",
        transaction_id="T_FULL_1",
        amount=Decimal("75.00"),
        currency="USD",
        provider_id="P3",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_FULL_1",
        transaction_id="T_FULL_1",
        status="success",
        actual_amount=Decimal("75.00"),
        actual_currency="USD",
        provider_id="P3",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for matched pair to appear (should NOT be blocked by full scoring bus)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(p.transaction.transaction_id == "T_FULL_1" for p in matched_pairs):
            break
        time.sleep(0.2)

    # Verify matched pair was collected in sink (stream not blocked)
    assert any(
        p.transaction.transaction_id == "T_FULL_1" for p in matched_pairs
    ), "Stream processing was blocked by full scoring bus"

    # Clean up: drain scoring bus
    while scoring_bus.dequeue_nowait() is not None:
        pass
