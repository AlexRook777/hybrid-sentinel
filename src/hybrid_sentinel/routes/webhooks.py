"""Webhook endpoints for transaction and callback event ingestion."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status

from hybrid_sentinel.event_bus import event_bus
from hybrid_sentinel.models import IncomingEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/transaction", status_code=status.HTTP_202_ACCEPTED)
async def ingest_transaction_event(
    event: Annotated[IncomingEvent, Body()],
) -> dict:
    """Ingest a transaction or callback event.

    Args:
        event: TransactionEvent or CallbackEvent (discriminated by type field).

    Returns:
        Acceptance status.

    Raises:
        HTTPException: 422 if validation fails, 503 if queue is full.
    """
    # Try to enqueue the event
    success = event_bus.enqueue(event)

    if not success:
        logger.warning("Event queue is full, rejecting event: %s", event.type)
        raise HTTPException(status_code=503, detail={"status": "overloaded"})

    logger.debug("Event accepted: type=%s", event.type)
    return {"status": "accepted"}
