"""Tests for LangGraph agent nodes."""

from hybrid_sentinel.agent.nodes import analyze_patterns, generate_report
from hybrid_sentinel.config import settings


def test_analyze_provider_outage_critical():
    state = {
        "provider_stats": {"affected_merchants": 5, "failure_rate": 0.15},
        "merchant_stats": {"failure_rate": 0.0},
        "anomaly_event": {},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "provider_outage"
    assert result["severity"] == "CRITICAL"


def test_analyze_provider_outage_high():
    state = {
        "provider_stats": {"affected_merchants": 3, "failure_rate": 0.11},
        "merchant_stats": {"failure_rate": 0.0},
        "anomaly_event": {},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "provider_outage"
    assert result["severity"] == "HIGH"


def test_analyze_merchant_targeting():
    """merchant_failure_rate > 5x provider_failure_rate AND affected <= 1."""
    state = {
        "provider_stats": {"affected_merchants": 1, "failure_rate": 0.02},
        "merchant_stats": {"failure_rate": 0.11},  # > 5 * 0.02 = 0.10
        "anomaly_event": {},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "merchant_targeting"
    assert result["severity"] == "HIGH"


def test_analyze_merchant_targeting_not_triggered_below_5x():
    """merchant_failure_rate <= 5x provider_failure_rate → behavioral."""
    state = {
        "provider_stats": {"affected_merchants": 1, "failure_rate": 0.10},
        "merchant_stats": {"failure_rate": 0.49},  # <= 5 * 0.10 = 0.50
        "anomaly_event": {},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "behavioral"


def test_analyze_timeout_cluster():
    state = {
        "provider_stats": {"affected_merchants": 2, "failure_rate": 0.06},
        "merchant_stats": {"failure_rate": 0.0},
        "anomaly_event": {"anomaly_type": "TIMEOUT"},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "timeout_cluster"
    assert result["severity"] == "MEDIUM"


def test_analyze_behavioral_catchall_medium():
    state = {
        "provider_stats": {"affected_merchants": 0, "failure_rate": 0.0},
        "merchant_stats": {"failure_rate": 0.0},
        "anomaly_event": {"anomaly_score": 0.96},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "behavioral"
    assert result["severity"] == "MEDIUM"


def test_analyze_behavioral_catchall_low():
    state = {
        "provider_stats": {"affected_merchants": 0, "failure_rate": 0.0},
        "merchant_stats": {"failure_rate": 0.0},
        "anomaly_event": {"anomaly_score": 0.86},
    }
    result = analyze_patterns(state)
    assert result["pattern"] == "behavioral"
    assert result["severity"] == "LOW"


def test_generate_report_mock():
    settings.agent_llm_model = "mock"
    state = {
        "pattern": "timeout_cluster",
        "severity": "MEDIUM",
        "anomaly_event": {},
    }
    result = generate_report(state)
    assert "MEDIUM" in result["recommendation"]
    assert "timeout_cluster" in result["recommendation"]


def test_generate_report_llm_fallback():
    settings.agent_llm_model = "fake-model-does-not-exist"
    state = {
        "pattern": "merchant_targeting",
        "severity": "HIGH",
        "anomaly_event": {},
    }
    result = generate_report(state)
    assert "FALLBACK" in result["recommendation"]
