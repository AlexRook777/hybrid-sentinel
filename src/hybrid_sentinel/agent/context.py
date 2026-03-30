"""Merchant and provider context computation for the investigation agent."""

from datetime import UTC, datetime, timedelta

from hybrid_sentinel.stream.sink import matched_pairs


def compute_merchant_stats(merchant_id: str) -> dict:
    """Compute historical statistics for a merchant.

    Returns:
        Dict containing failure_rate, avg_latency, event_count.
    """
    pairs = list(matched_pairs)  # shallow copy for thread safety

    merchant_pairs = [
        p for p in pairs if p.transaction.merchant_id == merchant_id
    ]

    event_count = len(merchant_pairs)
    if event_count == 0:
        return {
            "failure_rate": 0.0,
            "avg_latency": 0.0,
            "event_count": 0,
        }

    failures = sum(
        1 for p in merchant_pairs if p.callback.status == "failure"
    )
    failure_rate = float(failures) / event_count

    total_latency = sum(
        (p.callback.timestamp - p.transaction.timestamp).total_seconds()
        for p in merchant_pairs
    )
    avg_latency = float(total_latency) / event_count

    return {
        "failure_rate": failure_rate,
        "avg_latency": avg_latency,
        "event_count": event_count,
    }


def compute_provider_stats(
    provider_id: str,
    lookback_minutes: int,
    current_time: datetime | None = None,
) -> dict:
    """Compute recent statistics for a provider.

    Returns:
        Dict containing failure_rate, affected_merchants, total_merchants.
    """
    pairs = list(matched_pairs)
    now = current_time or datetime.now(UTC)
    cutoff_time = now - timedelta(minutes=lookback_minutes)

    provider_pairs = [
        p
        for p in pairs
        if p.transaction.provider_id == provider_id
        and p.transaction.timestamp >= cutoff_time
    ]

    total_merchants = len(
        {p.transaction.merchant_id for p in provider_pairs}
    )
    if not provider_pairs:
        return {
            "failure_rate": 0.0,
            "affected_merchants": 0,
            "total_merchants": 0,
        }

    failure_pairs = [
        p for p in provider_pairs if p.callback.status == "failure"
    ]
    failure_rate = float(len(failure_pairs)) / len(provider_pairs)
    affected_merchants = len(
        {p.transaction.merchant_id for p in failure_pairs}
    )

    return {
        "failure_rate": failure_rate,
        "affected_merchants": affected_merchants,
        "total_merchants": total_merchants,
    }
