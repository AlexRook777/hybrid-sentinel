"""Tests for agent lifecycle and background thread processing."""

import time
from datetime import UTC, datetime

import pytest

import hybrid_sentinel.stream.sink as sink
from hybrid_sentinel.agent import investigation_bus, start_agent, stop_agent
from hybrid_sentinel.agent.store import clear_cases, get_recent_cases
from hybrid_sentinel.config import settings
from hybrid_sentinel.models import AnomalyEvent


@pytest.fixture(autouse=True)
def clean_state():
    """Reset queues and lists before each test."""
    investigation_bus.reset()
    clear_cases()
    sink.matched_pairs.clear()
    settings.agent_enabled = True
    settings.agent_llm_model = "mock"
    yield
    stop_agent()
    investigation_bus.reset()
    clear_cases()
    sink.matched_pairs.clear()


def test_agent_background_processing():
    """Test that the agent thread processes events from the bus."""
    start_agent()

    investigation_bus.enqueue(
        AnomalyEvent(
            anomaly_type="TIMEOUT",
            merchant_id="m99",
            transaction_id="tx99",
            provider_id="p99",
            timestamp=datetime.now(UTC),
            anomaly_score=0.9,
            details={},
        )
    )

    time.sleep(1.0)

    cases = get_recent_cases()
    assert len(cases) == 1
    assert cases[0].merchant_event_count == 0
    assert cases[0].anomaly_event.anomaly_type == "TIMEOUT"


def test_agent_lifecycle_disabled():
    """Test that agent doesn't start if disabled."""
    settings.agent_enabled = False
    start_agent()
    from hybrid_sentinel.agent import _agent_thread

    assert _agent_thread is None


def test_agent_stop():
    """Test clean stopping of agent."""
    start_agent()
    from hybrid_sentinel.agent import _agent_thread

    assert _agent_thread is not None
    assert _agent_thread.is_alive()
    stop_agent()
    assert not _agent_thread.is_alive()
