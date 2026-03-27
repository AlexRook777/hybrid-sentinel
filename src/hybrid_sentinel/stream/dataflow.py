"""Bytewax dataflow wiring: source → key → stateful_map → sink."""

import asyncio
import logging
import threading
from typing import Any

import bytewax.operators as op
from bytewax.dataflow import Dataflow

from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import CallbackEvent, TransactionEvent
from hybrid_sentinel.stream.processor import callback_matcher
from hybrid_sentinel.stream.sink import EventCollectorSink
from hybrid_sentinel.stream.source import EventQueueSource

logger = logging.getLogger(__name__)


def get_event_key(event: Any) -> str:
    """Extract key from event for partitioning.

    Args:
        event: TransactionEvent, CallbackEvent, or "TICK" string.

    Returns:
        Key string in format "merchant_id:transaction_id" or "TICK".
    """
    if isinstance(event, str):
        return event  # TICK events use their own key

    # Transaction and Callback events
    if isinstance(event, (TransactionEvent, CallbackEvent)):
        return f"{event.merchant_id}:{event.transaction_id}"

    return "UNKNOWN"


def build_dataflow() -> Dataflow:
    """Build the Bytewax dataflow for stream processing.

    Returns:
        Configured Bytewax Dataflow.
    """
    flow = Dataflow("hybrid-sentinel-stream")

    # Source: Read from event bus queue
    input_stream = op.input("event_source", flow, EventQueueSource())

    # Key events by merchant_id:transaction_id
    keyed_stream = op.key_on("key_events", input_stream, get_event_key)

    # Stateful callback matching with timeout detection
    matched_stream = op.stateful_map("callback_matcher", keyed_stream, callback_matcher)

    # Flatten the output lists (stateful_map returns lists)
    flattened_stream = op.flat_map("flatten", matched_stream, lambda x: x)  # type: ignore[arg-type]

    # Sink: Collect matched pairs and anomaly events
    op.output("event_collector", flattened_stream, EventCollectorSink())

    return flow


def tick_generator(stop_event: threading.Event) -> None:
    """Background thread that periodically injects TICK events.

    Args:
        stop_event: Threading event to signal shutdown.
    """
    interval = settings.tick_interval
    logger.info("Tick generator started (interval: %ds)", interval)

    while not stop_event.is_set():
        # Wait for interval or until stop signal
        if stop_event.wait(timeout=interval):
            break

        # Inject TICK event into the event bus
        # Use asyncio to call the async enqueue method
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(event_bus.enqueue("TICK"))
            loop.close()
            logger.debug("TICK event injected")
        except Exception as e:
            logger.error("Failed to inject TICK event: %s", e)

    logger.info("Tick generator stopped")
