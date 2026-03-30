"""LangGraph nodes for the investigation agent pipeline."""

import logging
import time
from uuid import uuid4

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from hybrid_sentinel.agent.context import (
    compute_merchant_stats,
    compute_provider_stats,
)
from hybrid_sentinel.agent.state import InvestigationState
from hybrid_sentinel.config import settings

logger = logging.getLogger(__name__)


def gather_context(state: InvestigationState) -> dict:
    """Gather historical context for the merchant and provider."""
    event = state["anomaly_event"]
    merchant_id = event.get("merchant_id", "")
    provider_id = event.get("provider_id", "")

    m_stats = compute_merchant_stats(merchant_id)
    p_stats = compute_provider_stats(
        provider_id, settings.agent_lookback_minutes
    )

    return {
        "merchant_stats": m_stats,
        "provider_stats": p_stats,
        "case_id": str(uuid4()),
        "investigation_start_ms": time.monotonic() * 1000,
    }


def analyze_patterns(state: InvestigationState) -> dict:
    """Classify the anomaly into a pattern and assign severity."""
    m_stats = state.get("merchant_stats", {})
    p_stats = state.get("provider_stats", {})
    event = state.get("anomaly_event", {})

    pattern = "behavioral"
    severity = "LOW"

    p_affected = p_stats.get("affected_merchants", 0)
    p_fail_rate = p_stats.get("failure_rate", 0.0)
    m_fail_rate = m_stats.get("failure_rate", 0.0)
    anomaly_type = event.get("anomaly_type", "")
    anomaly_score = event.get("anomaly_score", 0.0) or 0.0

    if p_affected >= 3 and p_fail_rate > 0.1:
        pattern = "provider_outage"
        severity = "CRITICAL" if p_affected >= 5 else "HIGH"
    elif m_fail_rate > 5 * p_fail_rate and p_affected <= 1:
        pattern = "merchant_targeting"
        severity = "HIGH"
    elif anomaly_type == "TIMEOUT" and p_fail_rate > 0.05:
        pattern = "timeout_cluster"
        severity = "MEDIUM"

    if pattern == "behavioral" and anomaly_score >= 0.95:
        severity = "MEDIUM"

    return {
        "pattern": pattern,
        "severity": severity,
    }


def _template_recommendation(severity: str, pattern: str) -> str:
    """Build a template-based recommendation without LLM."""
    return (
        f"[{severity}] Detected {pattern}. "
        "Verify provider status and merchant callback configs."
    )


def generate_report(state: InvestigationState) -> dict:
    """Generate a human-readable recommendation via LLM or template."""
    pattern = state.get("pattern", "unknown")
    severity = state.get("severity", "LOW")

    if (
        not settings.agent_llm_model
        or settings.agent_llm_model.lower() == "mock"
    ):
        return {
            "recommendation": _template_recommendation(
                severity, pattern
            ),
        }

    try:
        model = init_chat_model(settings.agent_llm_model)
        sys_msg = SystemMessage(
            content=(
                "You are a payment routing AI. "
                "Analyze the context and provide a "
                "1-sentence recommendation."
            ),
        )
        event_summary = state.get("anomaly_event")
        hum_msg = HumanMessage(
            content=(
                f"Pattern: {pattern}, Severity: {severity}, "
                f"Event: {event_summary}"
            ),
        )
        response = model.invoke([sys_msg, hum_msg])
        return {"recommendation": str(response.content)}
    except Exception:
        logger.warning(
            "LLM call failed for model %s, falling back to template",
            settings.agent_llm_model,
            exc_info=True,
        )
        return {
            "recommendation": (
                f"[FALLBACK] {_template_recommendation(severity, pattern)}"
            ),
        }
