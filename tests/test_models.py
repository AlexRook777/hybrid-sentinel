"""Unit tests for data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from hybrid_sentinel.models import (
    AnomalyEvent,
    CallbackEvent,
    MatchedPair,
    TransactionEvent,
)


def test_transaction_event_valid():
    """Valid transaction event is accepted."""
    event = TransactionEvent(
        merchant_id="M1",
        transaction_id="T100",
        amount=100.50,
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(timezone.utc),
    )
    assert event.type == "transaction"
    assert event.merchant_id == "M1"
    assert event.transaction_id == "T100"
    assert event.amount == 100.50


def test_transaction_event_missing_transaction_id():
    """Transaction event missing transaction_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransactionEvent(
            merchant_id="M1",
            amount=100.50,
            currency="USD",
            provider_id="P1",
            timestamp=datetime.now(timezone.utc),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("transaction_id",) for err in errors)


def test_transaction_event_empty_merchant_id():
    """Transaction event with empty merchant_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransactionEvent(
            merchant_id="",
            transaction_id="T100",
            amount=100.50,
            currency="USD",
            provider_id="P1",
            timestamp=datetime.now(timezone.utc),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("merchant_id",) for err in errors)


def test_callback_event_valid():
    """Valid callback event is accepted."""
    event = CallbackEvent(
        merchant_id="M1",
        transaction_id="T100",
        status="success",
        provider_id="P1",
        timestamp=datetime.now(timezone.utc),
    )
    assert event.type == "callback"
    assert event.status == "success"


def test_callback_event_invalid_status():
    """Callback event with invalid status is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="invalid_status",
            provider_id="P1",
            timestamp=datetime.now(timezone.utc),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("status",) for err in errors)


def test_anomaly_event_valid():
    """Valid anomaly event is accepted."""
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M1",
        transaction_id="T100",
        provider_id="P1",
        timestamp=datetime.now(timezone.utc),
    )
    assert event.type == "anomaly"
    assert event.anomaly_type == "TIMEOUT"
    assert event.details == {}


def test_anomaly_event_with_details():
    """Anomaly event with custom details is accepted."""
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M1",
        transaction_id="T100",
        provider_id="P1",
        timestamp=datetime.now(timezone.utc),
        details={"elapsed_seconds": 350},
    )
    assert event.details == {"elapsed_seconds": 350}


def test_matched_pair_valid():
    """Valid matched pair is accepted."""
    now = datetime.now(timezone.utc)
    transaction = TransactionEvent(
        merchant_id="M1",
        transaction_id="T100",
        amount=100.50,
        currency="USD",
        provider_id="P1",
        timestamp=now,
    )
    callback = CallbackEvent(
        merchant_id="M1",
        transaction_id="T100",
        status="success",
        provider_id="P1",
        timestamp=now,
    )
    pair = MatchedPair(
        transaction=transaction,
        callback=callback,
        match_timestamp=now,
    )
    assert pair.transaction.transaction_id == "T100"
    assert pair.callback.status == "success"
