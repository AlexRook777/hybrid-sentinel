"""Structured logging for investigation case reports."""

import logging
import time
from datetime import UTC, datetime

from hybrid_sentinel.agent.state import InvestigationState
from hybrid_sentinel.models import AnomalyEvent, CaseReport

logger = logging.getLogger(__name__)


def log_alert(state: InvestigationState) -> dict:
    """Log the structured case report and return the duration."""
    end_ms = time.monotonic() * 1000
    start_ms = state.get("investigation_start_ms", end_ms)
    duration_ms = int(end_ms - start_ms)

    event_dict = state["anomaly_event"]
    # Provide defaults to prevent serialization failures
    anomaly_event = AnomalyEvent(
        anomaly_type=event_dict.get("anomaly_type", "unknown"),
        merchant_id=event_dict.get("merchant_id", "unknown"),
        transaction_id=event_dict.get("transaction_id", "unknown"),
        provider_id=event_dict.get("provider_id", "unknown"),
        timestamp=event_dict.get("timestamp", datetime.now(UTC)),
        details=event_dict.get("details", {}),
        anomaly_score=event_dict.get("anomaly_score", 0.0),
    )

    m_stats = state.get("merchant_stats", {})
    p_stats = state.get("provider_stats", {})

    report = CaseReport(
        case_id=state.get("case_id", "unknown-case"),
        anomaly_event=anomaly_event,
        severity=state.get("severity", "LOW"),
        pattern=state.get("pattern", "behavioral"),
        merchant_failure_rate=m_stats.get("failure_rate", 0.0),
        merchant_avg_latency=m_stats.get("avg_latency", 0.0),
        merchant_event_count=m_stats.get("event_count", 0),
        provider_failure_rate=p_stats.get("failure_rate", 0.0),
        provider_affected_merchants=p_stats.get(
            "affected_merchants", 0
        ),
        recommendation=state.get("recommendation", ""),
        investigation_duration_ms=duration_ms,
        timestamp=datetime.now(UTC),
    )

    # Write to standard logger for MVP
    logger.info("CASE_REPORT: %s", report.model_dump_json())

    return {"case_report": report}
