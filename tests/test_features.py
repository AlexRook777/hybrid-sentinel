"""Tests for anomaly detection feature extraction."""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from hybrid_sentinel.anomaly.features import extract_features
from hybrid_sentinel.models import (
    AnomalyEvent,
    CallbackEvent,
    MatchedPair,
    TransactionEvent,
)


def test_extract_features_from_matched_pair_normal_case():
    """Feature extraction from MatchedPair with normal transaction."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M1",
        transaction_id="T100",
        amount=Decimal("500.00"),
        currency="USD",
        provider_id="P1",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M1",
        transaction_id="T100",
        status="success",
        actual_amount=Decimal("500.00"),
        actual_currency="USD",
        provider_id="P1",
        timestamp=now + timedelta(seconds=2.5),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)

    features = extract_features(pair)

    assert "amount_log" in features
    # amount_log is normalized: log(500) / 15.0 ≈ 0.414
    assert math.isclose(features["amount_log"], math.log(500.0) / 15.0, rel_tol=0.01)
    # callback_latency_s is normalized: 2.5 / 300 ≈ 0.00833
    assert math.isclose(features["callback_latency_s"], 2.5 / 300.0, abs_tol=0.001)
    # Raw values preserved for classification
    assert math.isclose(features["callback_latency_s_raw"], 2.5, abs_tol=0.01)
    assert features["is_success"] == 1.0
    assert features["is_failure"] == 0.0
    assert features["is_amount_mismatch"] == 0.0
    assert features["amount_mismatch_pct"] == 0.0
    assert features["amount_mismatch_pct_raw"] == 0.0
    assert features["is_timeout"] == 0.0
    # All features should be in [0, 1]
    for key, val in features.items():
        if not key.endswith("_raw"):
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0,1]"


def test_extract_features_from_matched_pair_amount_mismatch():
    """Feature extraction from MatchedPair with amount mismatch."""
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

    assert features["is_amount_mismatch"] == 1.0
    # amount_mismatch_pct is normalized: 15.0 / 100.0 = 0.15
    assert math.isclose(features["amount_mismatch_pct"], 0.15, rel_tol=0.01)
    # Raw value preserved for classification
    assert math.isclose(features["amount_mismatch_pct_raw"], 15.0, rel_tol=0.01)


def test_extract_features_from_matched_pair_currency_mismatch():
    """Feature extraction from MatchedPair with currency mismatch."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M3",
        transaction_id="T300",
        amount=Decimal("200.00"),
        currency="USD",
        provider_id="P3",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M3",
        transaction_id="T300",
        status="success",
        actual_amount=Decimal("200.00"),
        actual_currency="EUR",  # Different currency
        provider_id="P3",
        timestamp=now + timedelta(seconds=3.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)

    features = extract_features(pair)

    assert features["is_amount_mismatch"] == 1.0


def test_extract_features_from_matched_pair_failure():
    """Feature extraction from MatchedPair with failure status."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M4",
        transaction_id="T400",
        amount=Decimal("75.50"),
        currency="USD",
        provider_id="P4",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M4",
        transaction_id="T400",
        status="failure",
        actual_amount=Decimal("75.50"),
        actual_currency="USD",
        provider_id="P4",
        timestamp=now + timedelta(seconds=4.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)

    features = extract_features(pair)

    assert features["is_success"] == 0.0
    assert features["is_failure"] == 1.0


def test_extract_features_round_amount():
    """Feature extraction detects round amounts (multiples of 100)."""
    now = datetime.now(UTC)
    txn = TransactionEvent(
        merchant_id="M5",
        transaction_id="T500",
        amount=Decimal("1000.00"),
        currency="USD",
        provider_id="P5",
        timestamp=now,
    )
    cb = CallbackEvent(
        merchant_id="M5",
        transaction_id="T500",
        status="success",
        actual_amount=Decimal("1000.00"),
        actual_currency="USD",
        provider_id="P5",
        timestamp=now + timedelta(seconds=1.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=now)

    features = extract_features(pair)

    assert features["is_round_amount"] == 1.0


def test_extract_features_from_timeout_anomaly_event():
    """Feature extraction from TIMEOUT AnomalyEvent uses sentinel values."""
    now = datetime.now(UTC)
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M6",
        transaction_id="T600",
        provider_id="P6",
        timestamp=now,
    )

    features = extract_features(event)

    # Sentinel values for TIMEOUT (latency normalized: 300/300 = 1.0)
    assert features["callback_latency_s"] == 1.0
    assert features["callback_latency_s_raw"] == 300.0
    assert features["is_success"] == 0.0
    assert features["is_failure"] == 0.0
    assert features["is_amount_mismatch"] == 0.0
    assert features["amount_mismatch_pct"] == 0.0
    assert features["is_timeout"] == 1.0
    # All features should be in [0, 1]
    for key, val in features.items():
        if not key.endswith("_raw"):
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0,1]"


def test_extract_features_from_timeout_has_temporal_features():
    """TIMEOUT AnomalyEvent still has temporal features extracted."""
    # Create event at a specific time
    timestamp = datetime(2026, 3, 27, 15, 30, tzinfo=UTC)  # Thursday 15:30
    event = AnomalyEvent(
        anomaly_type="TIMEOUT",
        merchant_id="M7",
        transaction_id="T700",
        provider_id="P7",
        timestamp=timestamp,
    )

    features = extract_features(event)

    # Check temporal features
    assert "hour_of_day" in features
    assert "day_of_week" in features
    assert features["hour_of_day"] > 0
    assert features["day_of_week"] > 0


def test_temporal_features_normalized_hour():
    """Temporal hour_of_day feature is normalized to [0, 1)."""
    # Create transaction at 15:00 (3 PM)
    timestamp = datetime(2026, 3, 27, 15, 0, tzinfo=UTC)
    txn = TransactionEvent(
        merchant_id="M8",
        transaction_id="T800",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P8",
        timestamp=timestamp,
    )
    cb = CallbackEvent(
        merchant_id="M8",
        transaction_id="T800",
        status="success",
        actual_amount=Decimal("100.00"),
        actual_currency="USD",
        provider_id="P8",
        timestamp=timestamp + timedelta(seconds=1.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=timestamp)

    features = extract_features(pair)

    # 15 / 24 = 0.625
    assert math.isclose(features["hour_of_day"], 0.625, abs_tol=0.001)
    assert 0 <= features["hour_of_day"] < 1


def test_temporal_features_normalized_day_of_week():
    """Temporal day_of_week feature is normalized to [0, 1)."""
    # Create transaction on Wednesday (weekday = 2)
    timestamp = datetime(2026, 3, 25, 12, 0, tzinfo=UTC)  # Wednesday
    txn = TransactionEvent(
        merchant_id="M9",
        transaction_id="T900",
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P9",
        timestamp=timestamp,
    )
    cb = CallbackEvent(
        merchant_id="M9",
        transaction_id="T900",
        status="success",
        actual_amount=Decimal("100.00"),
        actual_currency="USD",
        provider_id="P9",
        timestamp=timestamp + timedelta(seconds=1.0),
    )
    pair = MatchedPair(transaction=txn, callback=cb, match_timestamp=timestamp)

    features = extract_features(pair)

    # Wednesday weekday() = 2, so 2 / 7 ≈ 0.286
    assert math.isclose(features["day_of_week"], 2 / 7, abs_tol=0.001)
    assert 0 <= features["day_of_week"] < 1
