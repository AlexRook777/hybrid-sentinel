"""Bytewax stateful processor for callback matching and timeout detection."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from hybrid_sentinel.config import settings
from hybrid_sentinel.models import (
    AnomalyEvent,
    CallbackEvent,
    IncomingEvent,
    MatchedPair,
    TransactionEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class TransactionState:
    """State holding a pending transaction awaiting callback."""

    transaction: TransactionEvent
    received_at: datetime


class CallbackMatcherState:
    """State class for stateful callback matching."""

    def __init__(self) -> None:
        """Initialize empty state."""
        self.pending_transactions: dict[str, TransactionState] = {}

    def process_event(
        self, event: IncomingEvent
    ) -> tuple["CallbackMatcherState", list[Any]]:
        """Process an incoming event and return updated state and outputs.

        Args:
            event: TransactionEvent or CallbackEvent.

        Returns:
            Tuple of (updated_state, list_of_outputs).
            Outputs can be MatchedPair or AnomalyEvent.
        """
        outputs = []

        if isinstance(event, TransactionEvent):
            # Store transaction in state
            key = f"{event.merchant_id}:{event.transaction_id}"
            self.pending_transactions[key] = TransactionState(
                transaction=event,
                received_at=datetime.now(UTC),
            )
            logger.debug("Stored transaction in state: %s", key)

        elif isinstance(event, CallbackEvent):
            # Try to match with pending transaction
            key = f"{event.merchant_id}:{event.transaction_id}"
            if key in self.pending_transactions:
                state = self.pending_transactions.pop(key)
                matched = MatchedPair(
                    transaction=state.transaction,
                    callback=event,
                    match_timestamp=datetime.now(UTC),
                )
                outputs.append(matched)
                logger.debug("Matched callback to transaction: %s", key)
            else:
                logger.warning("Orphaned callback (no matching transaction): %s", key)

        return self, outputs

    def check_timeouts(self) -> tuple["CallbackMatcherState", list[Any]]:
        """Check for timed-out transactions and emit anomaly events.

        Returns:
            Tuple of (updated_state, list_of_anomaly_events).
        """
        now = datetime.now(UTC)
        timeout_seconds = settings.callback_timeout
        outputs = []
        timed_out_keys = []

        for key, state in self.pending_transactions.items():
            elapsed = (now - state.received_at).total_seconds()
            if elapsed > timeout_seconds:
                anomaly = AnomalyEvent(
                    anomaly_type="TIMEOUT",
                    merchant_id=state.transaction.merchant_id,
                    transaction_id=state.transaction.transaction_id,
                    provider_id=state.transaction.provider_id,
                    timestamp=now,
                    details={"elapsed_seconds": int(elapsed)},
                )
                outputs.append(anomaly)
                timed_out_keys.append(key)
                logger.info("TIMEOUT anomaly detected: %s (elapsed: %ds)", key, elapsed)

        # Remove timed-out entries from state
        for key in timed_out_keys:
            del self.pending_transactions[key]

        return self, outputs


def callback_matcher(
    state: CallbackMatcherState | None, event: Any
) -> tuple[CallbackMatcherState, list[Any]]:
    """Stateful mapper function for callback matching.

    Args:
        state: Current state (None on first event for this key).
        event: Incoming event (TransactionEvent, CallbackEvent, or "TICK").

    Returns:
        Tuple of (updated_state, list_of_outputs).
    """
    # Initialize state if None
    if state is None:
        state = CallbackMatcherState()

    # Handle tick events for timeout checks
    if isinstance(event, str) and event == "TICK":
        return state.check_timeouts()

    # Process normal events (must be IncomingEvent at this point)
    if isinstance(event, (TransactionEvent, CallbackEvent)):
        return state.process_event(event)

    # Unknown event type - ignore
    logger.warning("Unknown event type: %s", type(event))
    return state, []
