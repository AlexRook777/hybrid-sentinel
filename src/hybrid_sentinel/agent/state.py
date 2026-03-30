"""State definitions for the investigation agent LangGraph pipeline."""

from typing import TypedDict


class InvestigationState(TypedDict, total=False):
    """LangGraph state for anomaly investigation.

    Fields are populated progressively as the graph executes:
    - gather_context: anomaly_event, merchant_stats, provider_stats,
      case_id, investigation_start_ms
    - analyze_patterns: pattern, severity
    - generate_report: recommendation
    - log_alert: case_report (CaseReport model instance)
    """

    anomaly_event: dict
    merchant_stats: dict
    provider_stats: dict
    severity: str
    pattern: str
    recommendation: str
    case_id: str
    investigation_start_ms: float
    case_report: dict  # CaseReport model set by log_alert node
