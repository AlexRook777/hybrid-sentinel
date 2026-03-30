"""Hybrid Sentinel FastAPI application."""

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from bytewax.testing import run_main
from fastapi import FastAPI

from hybrid_sentinel import __version__
from hybrid_sentinel.agent import start_agent, stop_agent
from hybrid_sentinel.anomaly import start_scorer, stop_scorer
from hybrid_sentinel.config import settings
from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.routes import anomalies, cases, webhooks
from hybrid_sentinel.stream.dataflow import build_dataflow, tick_generator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler for startup and shutdown."""
    logging.basicConfig(level=settings.log_level)
    logger.info(
        "Starting %s v%s on %s:%s",
        settings.app_name,
        __version__,
        settings.host,
        settings.port,
    )

    # Build the Bytewax dataflow
    flow = build_dataflow()

    # Start the tick generator thread
    stop_event = threading.Event()
    tick_thread = threading.Thread(
        target=tick_generator, args=(stop_event,), daemon=True
    )
    tick_thread.start()
    logger.info("Tick generator thread started")

    # Start the Bytewax dataflow in a background thread
    dataflow_thread = threading.Thread(target=run_main, args=(flow,), daemon=True)
    dataflow_thread.start()
    logger.info("Bytewax dataflow thread started")

    # Start the anomaly scorer
    start_scorer()
    logger.info("Anomaly scorer started")

    # Start the investigation agent
    start_agent()
    logger.info("Investigation agent started")

    yield

    # Shutdown: stop the tick generator
    logger.info("Shutting down...")
    stop_event.set()

    # Stop the anomaly scorer
    stop_scorer()

    # Stop the investigation agent
    stop_agent()

    # Stop the event bus
    event_bus.stop()

    # Wait for threads to finish (with timeout)
    tick_thread.join(timeout=5)
    dataflow_thread.join(timeout=5)

    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
)

# Register routers
app.include_router(webhooks.router)
app.include_router(anomalies.router)
app.include_router(cases.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


