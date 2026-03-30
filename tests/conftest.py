"""Shared test fixtures."""

import threading
from collections.abc import Iterator

import pytest
from bytewax.testing import run_main
from fastapi.testclient import TestClient

from hybrid_sentinel.anomaly import scoring_bus, start_scorer, stop_scorer
from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.main import app
from hybrid_sentinel.stream.dataflow import build_dataflow, tick_generator
from hybrid_sentinel.stream.processor import clear_active_keys
from hybrid_sentinel.stream.sink import anomaly_events, matched_pairs


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def stream_pipeline() -> Iterator[None]:
    """Start the full stream processing pipeline for integration tests.

    Sets up event bus, dataflow thread, tick generator, and anomaly scorer.
    Tears everything down afterwards so state doesn't leak between tests.
    """
    # Reset all shared state
    event_bus.reset()
    scoring_bus.reset()
    matched_pairs.clear()
    anomaly_events.clear()
    clear_active_keys()

    # Shorten timeouts for fast integration tests
    original_timeout = settings.callback_timeout
    original_tick = settings.tick_interval
    settings.callback_timeout = 2
    settings.tick_interval = 1

    flow = build_dataflow()
    stop_event = threading.Event()

    tick_thread = threading.Thread(
        target=tick_generator, args=(stop_event,), daemon=True
    )
    tick_thread.start()

    dataflow_thread = threading.Thread(
        target=run_main, args=(flow,), daemon=True
    )
    dataflow_thread.start()

    # Start anomaly scorer
    start_scorer()

    yield

    # Shutdown scorer first (it consumes from scoring bus)
    stop_scorer()
    stop_event.set()
    event_bus.stop()
    tick_thread.join(timeout=5)
    dataflow_thread.join(timeout=5)

    # Restore settings and clean up
    settings.callback_timeout = original_timeout
    settings.tick_interval = original_tick
    event_bus.reset()
    scoring_bus.reset()
    matched_pairs.clear()
    anomaly_events.clear()
    clear_active_keys()
