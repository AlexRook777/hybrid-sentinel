"""Tests for the full LangGraph pipeline execution."""

from datetime import UTC, datetime

import pytest

import hybrid_sentinel.stream.sink as sink
from hybrid_sentinel.agent.graph import build_investigation_graph
from hybrid_sentinel.config import settings


@pytest.fixture(autouse=True)
def clean_sink():
    """Reset matched_pairs before each test."""
    sink.matched_pairs.clear()
    yield
    sink.matched_pairs.clear()


def test_full_graph_execution():
    """Test the end-to-end execution of the LangGraph pipeline."""
    settings.agent_llm_model = "mock"

    graph = build_investigation_graph()

    initial_state = {
        "anomaly_event": {
            "anomaly_type": "TIMEOUT",
            "merchant_id": "m1",
            "provider_id": "p1",
            "anomaly_score": 0.88,
            "timestamp": datetime.now(UTC),
            "transaction_id": "tx-123",
            "details": {},
        },
    }

    result = graph.invoke(initial_state)

    assert "case_id" in result
    assert result["pattern"] == "behavioral"
    assert result["severity"] == "LOW"
    assert "recommendation" in result
    assert "LOW" in result["recommendation"]
