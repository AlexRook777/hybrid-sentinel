"""Hybrid Sentinel FastAPI application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from hybrid_sentinel import __version__
from hybrid_sentinel.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=settings.log_level)
    logger.info(
        "Starting %s v%s on %s:%s",
        settings.app_name,
        __version__,
        settings.host,
        settings.port,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


