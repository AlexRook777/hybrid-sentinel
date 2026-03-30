"""Integration tests for anomaly detection pipeline."""

import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hybrid_sentinel.anomaly import get_scorer, scoring_bus
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import CallbackEvent, TransactionEvent


@pytest.mark.integration
def test_end_to_end_matched_pair_scoring(stream_pipeline: None) -> None:
    """Full pipeline: transaction + callback → Bytewax → scoring bus → scorer."""
    scorer = get_scorer()
    assert scorer is not None, "Scorer should be running"

    # Clear scoring bus
    while scoring_bus.dequeue_nowait() is not None:
        pass

    # Record initial events processed
    initial_stats = scorer.get_stats()
    initial_processed = initial_stats["events_processed"]

    # Submit transaction + callback
    txn = TransactionEvent(
        merchant_id="M_E2E_1",
        transaction_id="T_E2E_1",
        amount=Decimal("150.00"),
        currency="USD",
        provider_id="P_E2E",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_E2E_1",
        transaction_id="T_E2E_1",
        status="success",
        actual_amount=Decimal("150.00"),
        actual_currency="USD",
        provider_id="P_E2E",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for scorer to process (events flow: webhook → Bytewax → scoring bus → scorer)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        stats = scorer.get_stats()
        if stats["events_processed"] > initial_processed:
            break
        time.sleep(0.5)

    # Verify scorer processed the event
    final_stats = scorer.get_stats()
    assert final_stats["events_processed"] > initial_processed, (
        "Scorer should have processed at least one event"
    )


@pytest.mark.integration
def test_end_to_end_timeout_scoring(stream_pipeline: None) -> None:
    """Full pipeline: transaction without callback → TIMEOUT → scoring bus → scorer."""
    scorer = get_scorer()
    assert scorer is not None

    # Clear scoring bus
    while scoring_bus.dequeue_nowait() is not None:
        pass

    # Record initial events processed
    initial_stats = scorer.get_stats()
    initial_processed = initial_stats["events_processed"]

    # Submit transaction WITHOUT callback
    txn = TransactionEvent(
        merchant_id="M_TIMEOUT_E2E",
        transaction_id="T_TIMEOUT_E2E",
        amount=Decimal("200.00"),
        currency="USD",
        provider_id="P_TIMEOUT",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)

    # Wait for TIMEOUT (configured as 2s in test fixture) + scorer processing
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        stats = scorer.get_stats()
        if stats["events_processed"] > initial_processed:
            break
        time.sleep(0.5)

    # Verify scorer processed the TIMEOUT event
    final_stats = scorer.get_stats()
    assert final_stats["events_processed"] > initial_processed, (
        "Scorer should have processed the TIMEOUT event"
    )
