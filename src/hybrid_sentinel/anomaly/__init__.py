"""Anomaly detection module for online ML scoring with River."""

from hybrid_sentinel.anomaly.scorer import AnomalyScorer
from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import EventBus

# Scoring bus instance for stream processor → anomaly scorer communication
scoring_bus = EventBus(max_size=settings.scoring_queue_max_size)

# Global scorer instance
_scorer: AnomalyScorer | None = None


def start_scorer() -> AnomalyScorer:
    """Start the anomaly scorer in a background thread.

    Returns:
        The scorer instance
    """
    global _scorer
    if _scorer is not None:
        raise RuntimeError("Scorer already started")

    _scorer = AnomalyScorer()
    _scorer.start(scoring_bus)
    return _scorer


def stop_scorer() -> None:
    """Stop the anomaly scorer thread."""
    global _scorer
    if _scorer is not None:
        _scorer.stop()
        _scorer = None


def get_scorer() -> AnomalyScorer | None:
    """Get the current scorer instance (or None if not started)."""
    return _scorer


__all__ = ["scoring_bus", "start_scorer", "stop_scorer", "get_scorer"]
