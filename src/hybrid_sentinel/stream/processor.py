"""Bytewax stateful processor for callback matching and timeout detection."""

import logging
import threading
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
class TickEvent:
    """Tick event routed to a specific key for timeout checking."""

    key: str


# Thread-safe registry of keys with pending transactions.
# The tick generator reads this to know which keys need timeout checks.
_active_keys_lock = threading.Lock()
_active_keys: set[str] = set()


def register_active_key(key: str) -> None:
    with _active_keys_lock:
        _active_keys.add(key)


def unregister_active_key(key: str) -> None:
    with _active_keys_lock:
        _active_keys.discard(key)


def get_active_keys() -> set[str]:
    with _active_keys_lock:
        return _active_keys.copy()


def clear_active_keys() -> None:
    with _active_keys_lock:
        _active_keys.clear()


@dataclass
class TransactionState:
    """State holding a pending transaction awaiting callback."""

    transaction: TransactionEvent
    received_at: datetime


class CallbackMatcherState:
    """State class for stateful callback matching."""

    def __init__(self) -> None:
        self.pending_transactions: dict[str, TransactionState] = {}

    def process_event(
        self, event: IncomingEvent
    ) -> tuple["CallbackMatcherState", list[Any]]:
        """Process an incoming event and return updated state and outputs."""
        outputs: list[Any] = []

        if isinstance(event, TransactionEvent):
            key = f"{event.merchant_id}:{event.transaction_id}"
            self.pending_transactions[key] = TransactionState(
                transaction=event,
                received_at=datetime.now(UTC),
            )
            register_active_key(key)
            logger.debug("Stored transaction in state: %s", key)

        elif isinstance(event, CallbackEvent):
            key = f"{event.merchant_id}:{event.transaction_id}"
            if key in self.pending_transactions:
                state = self.pending_transactions.pop(key)
                matched = MatchedPair(
                    transaction=state.transaction,
                    callback=event,
                    match_timestamp=datetime.now(UTC),
                )
                outputs.append(matched)
                unregister_active_key(key)
                logger.debug("Matched callback to transaction: %s", key)
            else:
                logger.warning("Orphaned callback (no matching transaction): %s", key)

        return self, outputs

    def check_timeouts(self) -> tuple["CallbackMatcherState", list[Any]]:
        """Check for timed-out transactions and emit anomaly events."""
        now = datetime.now(UTC)
        timeout_seconds = settings.callback_timeout
        outputs: list[Any] = []
        timed_out_keys: list[str] = []

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

        for key in timed_out_keys:
            del self.pending_transactions[key]
            unregister_active_key(key)

        return self, outputs


def callback_matcher(
    state: CallbackMatcherState | None, event: Any
) -> tuple[CallbackMatcherState, list[Any]]:
    """Stateful mapper function for callback matching.

    Args:
        state: Current state (None on first event for this key).
        event: Incoming event (TransactionEvent, CallbackEvent, or TickEvent).

    Returns:
        Tuple of (updated_state, list_of_outputs).
    """
    if state is None:
        state = CallbackMatcherState()

    if isinstance(event, TickEvent):
        return state.check_timeouts()

    if isinstance(event, (TransactionEvent, CallbackEvent)):
        return state.process_event(event)

    logger.warning("Unknown event type: %s", type(event))
    return state, []
