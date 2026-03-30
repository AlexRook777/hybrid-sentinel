"""Feature extraction for anomaly detection.

All features are normalized to [0, 1] for River HalfSpaceTrees which assumes
this range by default. Raw (unnormalized) values for callback_latency_s and
amount_mismatch_pct are stored alongside for use in classification logic.
"""

import math
from decimal import Decimal

from hybrid_sentinel.models import AnomalyEvent, MatchedPair

# Normalization bounds for features that exceed [0, 1].
# These are generous upper bounds — values above are clamped to 1.0.
_MAX_AMOUNT_LOG = 15.0  # log(~3.3M) — covers most transaction amounts
_MAX_LATENCY_S = 300.0  # Callback timeout ceiling
_MAX_MISMATCH_PCT = 100.0  # Cap at 100%
_MAX_HASH_BUCKET = 63.0  # hash % 64 → [0, 63]


def _clamp01(value: float) -> float:
    """Clamp a value to [0, 1]."""
    return max(0.0, min(1.0, value))


def extract_features(event: MatchedPair | AnomalyEvent) -> dict[str, float]:
    """Extract feature vector from MatchedPair or AnomalyEvent for River scoring.

    Args:
        event: MatchedPair (transaction + callback) or AnomalyEvent (TIMEOUT)

    Returns:
        Dictionary of feature names to float values normalized to [0, 1].
        Raw values for latency and mismatch are included with ``_raw`` suffix
        for use in anomaly classification.
    """
    if isinstance(event, MatchedPair):
        return _extract_from_matched_pair(event)
    elif isinstance(event, AnomalyEvent):
        return _extract_from_anomaly_event(event)
    else:
        raise TypeError(f"Unsupported event type: {type(event)}")


def _extract_from_matched_pair(pair: MatchedPair) -> dict[str, float]:
    """Extract features from a MatchedPair (transaction + callback)."""
    txn = pair.transaction
    cb = pair.callback

    # Amount features
    amount_float = float(txn.amount)
    amount_log_raw = math.log(amount_float) if amount_float > 0 else 0.0
    amount_log = _clamp01(amount_log_raw / _MAX_AMOUNT_LOG)
    is_round_amount = 1.0 if txn.amount % 100 == 0 else 0.0

    # Latency feature
    callback_latency_raw = (cb.timestamp - txn.timestamp).total_seconds()
    callback_latency_s = _clamp01(callback_latency_raw / _MAX_LATENCY_S)

    # Status features
    is_success = 1.0 if cb.status == "success" else 0.0
    is_failure = 1.0 if cb.status == "failure" else 0.0

    # Amount mismatch features
    expected_amount = float(txn.amount)
    actual_amount = float(cb.actual_amount)
    is_amount_mismatch = 1.0 if (
        actual_amount != expected_amount or cb.actual_currency != txn.currency
    ) else 0.0

    amount_mismatch_pct_raw = 0.0
    if expected_amount > 0:
        amount_mismatch_pct_raw = abs(actual_amount - expected_amount) / expected_amount * 100
    amount_mismatch_pct = _clamp01(amount_mismatch_pct_raw / _MAX_MISMATCH_PCT)

    # Temporal features (already in [0, 1))
    hour_of_day = txn.timestamp.hour / 24.0
    day_of_week = txn.timestamp.weekday() / 7.0

    # Categorical features (hash to buckets, normalized)
    provider_hash = (hash(txn.provider_id) % 64) / _MAX_HASH_BUCKET
    merchant_hash = (hash(txn.merchant_id) % 64) / _MAX_HASH_BUCKET

    # Is timeout
    is_timeout = 0.0

    return {
        "amount_log": amount_log,
        "callback_latency_s": callback_latency_s,
        "is_success": is_success,
        "is_failure": is_failure,
        "is_amount_mismatch": is_amount_mismatch,
        "amount_mismatch_pct": amount_mismatch_pct,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "is_round_amount": is_round_amount,
        "provider_hash": provider_hash,
        "merchant_hash": merchant_hash,
        "is_timeout": is_timeout,
        # Raw values for classification (not fed to the model)
        "callback_latency_s_raw": callback_latency_raw,
        "amount_mismatch_pct_raw": amount_mismatch_pct_raw,
    }


def _extract_from_anomaly_event(event: AnomalyEvent) -> dict[str, float]:
    """Extract features from an AnomalyEvent (TIMEOUT).

    For TIMEOUT events (no callback), use sentinel values for callback-dependent features.
    """
    # We don't have the original transaction amount in AnomalyEvent
    # Use 0.0 as a sentinel (Phase 3 may pass transaction amount through details)
    amount_log = 0.0
    is_round_amount = 0.0

    # TIMEOUT sentinel values (latency = timeout ceiling → normalized to 1.0)
    callback_latency_s = 1.0  # 300/300 = 1.0
    callback_latency_raw = 300.0
    is_success = 0.0
    is_failure = 0.0
    is_amount_mismatch = 0.0
    amount_mismatch_pct = 0.0
    amount_mismatch_pct_raw = 0.0

    # Temporal features from TIMEOUT timestamp
    hour_of_day = event.timestamp.hour / 24.0
    day_of_week = event.timestamp.weekday() / 7.0

    # Categorical features (normalized)
    provider_hash = (hash(event.provider_id) % 64) / _MAX_HASH_BUCKET
    merchant_hash = (hash(event.merchant_id) % 64) / _MAX_HASH_BUCKET

    # Is timeout
    is_timeout = 1.0

    return {
        "amount_log": amount_log,
        "callback_latency_s": callback_latency_s,
        "is_success": is_success,
        "is_failure": is_failure,
        "is_amount_mismatch": is_amount_mismatch,
        "amount_mismatch_pct": amount_mismatch_pct,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "is_round_amount": is_round_amount,
        "provider_hash": provider_hash,
        "merchant_hash": merchant_hash,
        "is_timeout": is_timeout,
        # Raw values for classification
        "callback_latency_s_raw": callback_latency_raw,
        "amount_mismatch_pct_raw": amount_mismatch_pct_raw,
    }
