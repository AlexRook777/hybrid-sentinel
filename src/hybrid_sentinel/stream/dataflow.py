"""Bytewax dataflow wiring: source → key → stateful_map → sink."""

import logging
import threading
from typing import Any

import bytewax.operators as op
from bytewax.dataflow import Dataflow

from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import CallbackEvent, TransactionEvent
from hybrid_sentinel.stream.processor import (
    TickEvent,
    callback_matcher,
    get_active_keys,
)
from hybrid_sentinel.stream.sink import EventCollectorSink
from hybrid_sentinel.stream.source import EventQueueSource

logger = logging.getLogger(__name__)


def get_event_key(event: Any) -> str:
    """Extract key from event for partitioning.

    TickEvents carry their own key so they are routed to the correct
    state partition (the one holding the pending transaction).
    """
    if isinstance(event, TickEvent):
        return event.key

    if isinstance(event, (TransactionEvent, CallbackEvent)):
        return f"{event.merchant_id}:{event.transaction_id}"

    return "UNKNOWN"


def build_dataflow() -> Dataflow:
    """Build the Bytewax dataflow for stream processing."""
    flow = Dataflow("hybrid-sentinel-stream")

    input_stream = op.input("event_source", flow, EventQueueSource())
    keyed_stream = op.key_on("key_events", input_stream, get_event_key)
    matched_stream = op.stateful_map("callback_matcher", keyed_stream, callback_matcher)
    flattened_stream = op.flat_map(
        "flatten", matched_stream, lambda kv: kv[1]  # type: ignore[arg-type]
    )
    op.output("event_collector", flattened_stream, EventCollectorSink())

    return flow


def tick_generator(stop_event: threading.Event) -> None:
    """Background thread that periodically injects TickEvents.

    Reads the active keys registry and injects a TickEvent for each key,
    so every pending transaction's state partition gets a timeout check.
    """
    interval = settings.tick_interval
    logger.info("Tick generator started (interval: %ds)", interval)

    while not stop_event.is_set():
        if stop_event.wait(timeout=interval):
            break

        active = get_active_keys()
        for key in active:
            event_bus.enqueue(TickEvent(key=key))

        if active:
            logger.debug("TICK events injected for %d active keys", len(active))

    logger.info("Tick generator stopped")
