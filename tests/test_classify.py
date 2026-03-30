"""Tests for anomaly type classification."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hybrid_sentinel.anomaly.classify import classify_anomaly
from hybrid_sentinel.anomaly.features import extract_features
from hybrid_sentinel.models import (
    AnomalyEvent,
    CallbackEvent,
    MatchedPair,
    TransactionEvent,
)


def test_classify_timeout_event():
    """TIMEOUT AnomalyEvent is classified as TIMEOUT."""
    now = datetime.now(UTC)
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M1",
        transaction_id="T100",
        provider_id="P1",
        timestamp=now,
    )
    features = extract_features(event)
    anomaly_type = classify_anomaly(event, features, score=0.90, rolling_latency_mean=2.0)

    assert anomaly_type == "TIMEOUT"


def test_classify_amount_mismatch():
    """MatchedPair with amount_mismatch_pct > 10% is classified as AMOUNT_MISMATCH."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M2",
        transaction_id="T200",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P2",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M2",
        transaction_id="T200",
        status="success",
        actual_amount=Decimal("85.00"),  # 15% mismatch
        actual_currency="USD",
        provider_id="P2",
        timestamp=now + timedelta(seconds=1.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)
    features = extract_features(pair)

    anomaly_type = classify_anomaly(pair, features, score=0.92, rolling_latency_mean=2.0)

    assert anomaly_type == "AMOUNT_MISMATCH"


def test_classify_latency_spike():
    """MatchedPair with callback_latency > 3x rolling mean is classified as LATENCY_SPIKE."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M3",
        transaction_id="T300",
        amount=Decimal("50.00"),
        currency="USD",
        provider_id="P3",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M3",
        transaction_id="T300",
        status="success",
        actual_amount=Decimal("50.00"),
        actual_currency="USD",
        provider_id="P3",
        timestamp=now + timedelta(seconds=15.0),  # 15 seconds latency
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)
    features = extract_features(pair)

    # Rolling mean = 2.0, callback latency = 15.0 (> 3 * 2.0 = 6.0)
    anomaly_type = classify_anomaly(pair, features, score=0.88, rolling_latency_mean=2.0)

    assert anomaly_type == "LATENCY_SPIKE"


def test_classify_behavioral_catchall():
    """Anomaly with no specific sub-type is classified as BEHAVIORAL."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M4",
        transaction_id="T400",
        amount=Decimal("250.00"),
        currency="USD",
        provider_id="P4",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M4",
        transaction_id="T400",
        status="success",
        actual_amount=Decimal("250.00"),
        actual_currency="USD",
        provider_id="P4",
        timestamp=now + timedelta(seconds=2.5),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)
    features = extract_features(pair)

    # No amount mismatch, no latency spike
    anomaly_type = classify_anomaly(pair, features, score=0.90, rolling_latency_mean=2.0)

    assert anomaly_type == "BEHAVIORAL"


def test_classify_amount_mismatch_takes_precedence_over_latency():
    """AMOUNT_MISMATCH classification takes precedence over LATENCY_SPIKE."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M5",
        transaction_id="T500",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P5",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M5",
        transaction_id="T500",
        status="success",
        actual_amount=Decimal("80.00"),  # 20% mismatch
        actual_currency="USD",
        provider_id="P5",
        timestamp=now + timedelta(seconds=20.0),  # High latency too
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)
    features = extract_features(pair)

    # Both conditions met, but AMOUNT_MISMATCH should win
    anomaly_type = classify_anomaly(pair, features, score=0.95, rolling_latency_mean=2.0)

    assert anomaly_type == "AMOUNT_MISMATCH"
