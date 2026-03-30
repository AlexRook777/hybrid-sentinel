"""Agent investigation module initialization."""

import logging
import threading
from typing import Any

from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import EventBus

logger = logging.getLogger(__name__)

# Event bus for anomalies ready for investigation.
# Created lazily only when the agent is enabled; otherwise a no-op bus
# that silently drops events (max_size=0 is not valid, so we use a
# tiny bus that the scorer can enqueue to without errors).
investigation_bus: EventBus = EventBus(
    max_size=(
        settings.investigation_queue_max_size
        if settings.agent_enabled
        else 1
    )
)

_agent_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _agent_loop() -> None:
    """Background loop for consuming anomalies and running investigations."""
    from hybrid_sentinel.agent.graph import investigation_graph
    from hybrid_sentinel.agent.store import add_case

    while not _stop_event.is_set():
        event = investigation_bus.dequeue(timeout=0.5)
        if event is None:
            continue

        try:
            # invoke returns the final state dict
            state_dict = {"anomaly_event": event.model_dump()}
            final_state = investigation_graph.invoke(state_dict)
            if "case_report" in final_state:
                add_case(final_state["case_report"])
        except Exception:
            logger.exception("Investigation failed")


def start_agent() -> None:
    """Start the background investigation agent thread."""
    global _agent_thread

    if not settings.agent_enabled:
        logger.info("Investigation agent disabled via config")
        return

    _stop_event.clear()
    _agent_thread = threading.Thread(
        target=_agent_loop, name="InvestigationAgent", daemon=True
    )
    _agent_thread.start()
    logger.info("Investigation agent started")


def stop_agent() -> None:
    """Stop the background investigation agent thread."""
    global _agent_thread

    _stop_event.set()
    if _agent_thread is not None:
        _agent_thread.join(timeout=5.0)
        _agent_thread = None
    logger.info("Investigation agent stopped")


def get_agent() -> Any:
    """Get the compiled LangGraph investigation agent."""
    from hybrid_sentinel.agent.graph import investigation_graph

    return investigation_graph
