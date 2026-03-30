"""Unit tests for agent context computation."""

from datetime import UTC, datetime, timedelta

import pytest

import hybrid_sentinel.stream.sink as sink
from hybrid_sentinel.agent.context import (
    compute_merchant_stats,
    compute_provider_stats,
)
from hybrid_sentinel.models import CallbackEvent, MatchedPair, TransactionEvent


@pytest.fixture(autouse=True)
def clean_sink():
    """Reset matched_pairs before each test."""
    sink.matched_pairs.clear()
    yield
    sink.matched_pairs.clear()


def create_pair(
    merchant_id: str, 
    provider_id: str, 
    status: str, 
    time_offset_min: int = 0,
    latency_sec: int = 1
) -> MatchedPair:
    base_time = datetime.now(UTC) - timedelta(minutes=time_offset_min)
    cb_time = base_time + timedelta(seconds=latency_sec)
    
    txn = TransactionEvent(
        merchant_id=merchant_id,
        transaction_id="tx1",
        amount=100.0,
        currency="USD",
        provider_id=provider_id,
        timestamp=base_time
    )
    cb = CallbackEvent(
        merchant_id=merchant_id,
        transaction_id="tx1",
        status=status,
        actual_amount=100.0,
        actual_currency="USD",
        provider_id=provider_id,
        timestamp=cb_time
    )
    return MatchedPair(transaction=txn, callback=cb, match_timestamp=cb_time)


def test_merchant_stats_empty():
    stats = compute_merchant_stats("m1")
    assert stats["event_count"] == 0
    assert stats["failure_rate"] == 0.0
    assert stats["avg_latency"] == 0.0


def test_merchant_stats_normal():
    sink.matched_pairs.extend([
        create_pair("m1", "p1", "success", latency_sec=1),
        create_pair("m1", "p1", "failure", latency_sec=3),
        create_pair("m2", "p1", "success", latency_sec=10), # different merchant
    ])
    
    stats = compute_merchant_stats("m1")
    assert stats["event_count"] == 2
    assert stats["failure_rate"] == 0.5
    assert stats["avg_latency"] == 2.0


def test_provider_stats_empty():
    stats = compute_provider_stats("p1", lookback_minutes=10)
    assert stats["failure_rate"] == 0.0
    assert stats["total_merchants"] == 0
    assert stats["affected_merchants"] == 0


def test_provider_stats_lookback_window():
    sink.matched_pairs.extend([
        create_pair("m1", "p1", "success", time_offset_min=5),
        create_pair("m2", "p1", "failure", time_offset_min=8),
        create_pair("m3", "p1", "failure", time_offset_min=20), # Outside 10m window
        create_pair("m1", "p2", "failure", time_offset_min=2),  # Different provider
    ])
    
    stats = compute_provider_stats("p1", lookback_minutes=10)
    assert stats["total_merchants"] == 2 # m1, m2
    assert stats["affected_merchants"] == 1 # m2
    assert stats["failure_rate"] == 0.5
