"""Anomaly type classification based on features and score."""

from hybrid_sentinel.models import AnomalyEvent, MatchedPair


def classify_anomaly(
    event: MatchedPair | AnomalyEvent,
    features: dict[str, float],
    score: float,
    rolling_latency_mean: float,
) -> str:
    """Classify anomaly type based on feature analysis.

    Args:
        event: The source event (MatchedPair or AnomalyEvent)
        features: Extracted feature dictionary
        score: Anomaly score from River model
        rolling_latency_mean: Rolling mean of callback latency for comparison

    Returns:
        Anomaly type: TIMEOUT, AMOUNT_MISMATCH, LATENCY_SPIKE, or BEHAVIORAL
    """
    # TIMEOUT events maintain their type
    if isinstance(event, AnomalyEvent) and event.anomaly_type == "TIMEOUT":
        return "TIMEOUT"

    # AMOUNT_MISMATCH: mismatch percentage exceeds 10%
    if features.get("amount_mismatch_pct_raw", 0.0) > 10.0:
        return "AMOUNT_MISMATCH"

    # LATENCY_SPIKE: callback latency exceeds 3x rolling mean
    callback_latency = features.get("callback_latency_s_raw", 0.0)
    if rolling_latency_mean > 0 and callback_latency > 3 * rolling_latency_mean:
        return "LATENCY_SPIKE"

    # BEHAVIORAL: catch-all for other scored anomalies
    return "BEHAVIORAL"
