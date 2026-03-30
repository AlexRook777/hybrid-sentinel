"""Integration tests for stream processing pipeline.

These tests start the full Bytewax dataflow + tick generator, push
events through the event bus, and verify sink output.  They use short
timeouts (2 s callback, 1 s tick) set by the ``stream_pipeline`` fixture.
"""

import time
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import CallbackEvent, TransactionEvent
from hybrid_sentinel.stream.sink import anomaly_events, matched_pairs


@pytest.mark.integration
def test_transaction_callback_matching(stream_pipeline: None) -> None:
    """Submit transaction then callback — verify a MatchedPair is emitted."""
    txn = TransactionEvent(
        merchant_id="M_INT_1",
        transaction_id="T_MATCH_1",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_INT_1",
        transaction_id="T_MATCH_1",
        status="success",
        actual_amount=Decimal("100.00"),
        actual_currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for the dataflow to process both events
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(
            p.transaction.transaction_id == "T_MATCH_1" for p in matched_pairs
        ):
            break
        time.sleep(0.2)

    assert any(
        p.transaction.merchant_id == "M_INT_1"
        and p.transaction.transaction_id == "T_MATCH_1"
        and p.callback.status == "success"
        for p in matched_pairs
    ), f"Expected matched pair not found. Pairs: {len(matched_pairs)}"


@pytest.mark.integration
def test_reconciliation_different_amounts(stream_pipeline: None) -> None:
    """Submit transaction and callback with different amounts/currencies.

    Verify MatchedPair contains both original and actual values.
    """
    txn = TransactionEvent(
        merchant_id="M_INT_3",
        transaction_id="T_RECON_DIFF_1",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_INT_3",
        transaction_id="T_RECON_DIFF_1",
        status="success",
        actual_amount=Decimal("90.00"),  # Different amount
        actual_currency="EUR",  # Different currency
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for the dataflow to process both events
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(
            p.transaction.transaction_id == "T_RECON_DIFF_1" for p in matched_pairs
        ):
            break
        time.sleep(0.2)

    # Find the matched pair
    pair = next(
        (p for p in matched_pairs if p.transaction.transaction_id == "T_RECON_DIFF_1"),
        None,
    )
    assert pair is not None, "Expected matched pair not found"

    # Verify transaction values
    assert pair.transaction.amount == Decimal("100.00")
    assert pair.transaction.currency == "USD"

    # Verify callback actual values
    assert pair.callback.actual_amount == Decimal("90.00")
    assert pair.callback.actual_currency == "EUR"


@pytest.mark.integration
def test_reconciliation_same_amounts(stream_pipeline: None) -> None:
    """Submit transaction and callback with same amount/currency values.

    Verify MatchedPair contains matching values.
    """
    txn = TransactionEvent(
        merchant_id="M_INT_4",
        transaction_id="T_RECON_SAME_1",
        amount=Decimal("200.00"),
        currency="GBP",
        provider_id="P2",
        timestamp=datetime.now(UTC),
    )
    cb = CallbackEvent(
        merchant_id="M_INT_4",
        transaction_id="T_RECON_SAME_1",
        status="success",
        actual_amount=Decimal("200.00"),  # Same amount
        actual_currency="GBP",  # Same currency
        provider_id="P2",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)
    event_bus.enqueue(cb)

    # Wait for the dataflow to process both events
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if any(
            p.transaction.transaction_id == "T_RECON_SAME_1" for p in matched_pairs
        ):
            break
        time.sleep(0.2)

    # Find the matched pair
    pair = next(
        (p for p in matched_pairs if p.transaction.transaction_id == "T_RECON_SAME_1"),
        None,
    )
    assert pair is not None, "Expected matched pair not found"

    # Verify values match
    assert pair.transaction.amount == Decimal("200.00")
    assert pair.transaction.currency == "GBP"
    assert pair.callback.actual_amount == Decimal("200.00")
    assert pair.callback.actual_currency == "GBP"


@pytest.mark.integration
def test_timeout_anomaly_detection(stream_pipeline: None) -> None:
    """Submit transaction without callback — verify TIMEOUT anomaly is emitted.

    The ``stream_pipeline`` fixture sets callback_timeout=2 s and tick_interval=1 s,
    so a TIMEOUT should appear within ~4 s.
    """
    txn = TransactionEvent(
        merchant_id="M_INT_2",
        transaction_id="T_TIMEOUT_1",
        amount=Decimal("200.00"),
        currency="USD",
        provider_id="P2",
        timestamp=datetime.now(UTC),
    )

    event_bus.enqueue(txn)

    # Wait for timeout (2 s) + tick (1 s) + processing headroom
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if any(
            a.transaction_id == "T_TIMEOUT_1" and a.anomaly_type == "TIMEOUT"
            for a in anomaly_events
        ):
            break
        time.sleep(0.2)

    assert any(
        a.merchant_id == "M_INT_2"
        and a.transaction_id == "T_TIMEOUT_1"
        and a.anomaly_type == "TIMEOUT"
        for a in anomaly_events
    ), f"Expected TIMEOUT anomaly not found. Anomalies: {len(anomaly_events)}"
