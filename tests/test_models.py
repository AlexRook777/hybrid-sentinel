"""Unit tests for data models."""

from datetime import UTC, datetime
from decimal import Decimal

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
        amount=Decimal("100.50"),
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    assert event.type == "transaction"
    assert event.merchant_id == "M1"
    assert event.transaction_id == "T100"
    assert event.amount == Decimal("100.50")


def test_transaction_event_missing_transaction_id():
    """Transaction event missing transaction_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransactionEvent(
            merchant_id="M1",
            amount=Decimal("100.50"),
            currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("transaction_id",) for err in errors)


def test_transaction_event_empty_merchant_id():
    """Transaction event with empty merchant_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TransactionEvent(
            merchant_id="",
            transaction_id="T100",
            amount=Decimal("100.50"),
            currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("merchant_id",) for err in errors)


def test_callback_event_valid():
    """Valid callback event is accepted."""
    event = CallbackEvent(
        merchant_id="M1",
        transaction_id="T100",
        status="success",
        actual_amount=Decimal("100.50"),
        actual_currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    assert event.type == "callback"
    assert event.status == "success"
    assert event.actual_amount == Decimal("100.50")
    assert event.actual_currency == "USD"


def test_callback_event_invalid_status():
    """Callback event with invalid status is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="invalid_status",
            actual_amount=Decimal("100.50"),
            actual_currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("status",) for err in errors)


def test_callback_event_missing_actual_amount():
    """Callback event missing actual_amount is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_amount",) for err in errors)


def test_callback_event_missing_actual_currency():
    """Callback event missing actual_currency is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_amount=Decimal("100.50"),
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_currency",) for err in errors)


def test_callback_event_invalid_currency_length():
    """Callback event with invalid currency length is rejected."""
    # Test too short
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_amount=Decimal("100.50"),
            actual_currency="US",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_currency",) for err in errors)

    # Test too long
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_amount=Decimal("100.50"),
            actual_currency="DOLLAR",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_currency",) for err in errors)


def test_callback_event_zero_or_negative_amount():
    """Callback event with zero or negative amount is rejected."""
    # Test zero amount
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_amount=Decimal("0"),
            actual_currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_amount",) for err in errors)

    # Test negative amount
    with pytest.raises(ValidationError) as exc_info:
        CallbackEvent(
            merchant_id="M1",
            transaction_id="T100",
            status="success",
            actual_amount=Decimal("-10.50"),
            actual_currency="USD",
            provider_id="P1",
            timestamp=datetime.now(UTC),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("actual_amount",) for err in errors)


def test_anomaly_event_valid():
    """Valid anomaly event is accepted."""
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M1",
        transaction_id="T100",
        provider_id="P1",
        timestamp=datetime.now(UTC),
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
        timestamp=datetime.now(UTC),
        details={"elapsed_seconds": 350},
    )
    assert event.details == {"elapsed_seconds": 350}


def test_matched_pair_valid():
    """Valid matched pair is accepted."""
    now = datetime.now(UTC)
    transaction = TransactionEvent(
        merchant_id="M1",
        transaction_id="T100",
        amount=Decimal("100.50"),
        currency="USD",
        provider_id="P1",
        timestamp=now,
    )
    callback = CallbackEvent(
        merchant_id="M1",
        transaction_id="T100",
        status="success",
        actual_amount=Decimal("100.50"),
        actual_currency="USD",
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


def test_anomaly_event_phase1_timeout_no_score():
    """Phase 1 TIMEOUT events have anomaly_score=None."""
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M1",
        transaction_id="T200",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )
    assert event.anomaly_score is None


def test_anomaly_event_phase2_scored_with_float():
    """Phase 2 scored events have anomaly_score as float."""
    event = AnomalyEvent(
        anomaly_type="BEHAVIORAL",
        merchant_id="M2",
        transaction_id="T300",
        provider_id="P2",
        timestamp=datetime.now(UTC),
        anomaly_score=0.92,
    )
    assert isinstance(event.anomaly_score, float)
    assert event.anomaly_score == 0.92
