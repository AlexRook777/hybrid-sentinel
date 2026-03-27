"""Unit tests for webhook endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hybrid_sentinel.main import app


@pytest.mark.asyncio
async def test_ingest_valid_transaction_event():
    """Valid transaction event returns 202 Accepted."""
    payload = {
        "type": "transaction",
        "merchant_id": "M1",
        "transaction_id": "T100",
        "amount": 100.50,
        "currency": "USD",
        "provider_id": "P1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhooks/transaction", json=payload)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


@pytest.mark.asyncio
async def test_ingest_valid_callback_event():
    """Valid callback event returns 202 Accepted."""
    payload = {
        "type": "callback",
        "merchant_id": "M1",
        "transaction_id": "T100",
        "status": "success",
        "provider_id": "P1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhooks/transaction", json=payload)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


@pytest.mark.asyncio
async def test_ingest_invalid_payload():
    """Invalid payload returns 422 Unprocessable Entity."""
    payload = {
        "type": "transaction",
        "merchant_id": "M1",
        # Missing required fields: transaction_id, amount, currency, provider_id, timestamp
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhooks/transaction", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_ingest_invalid_callback_status():
    """Callback with invalid status returns 422."""
    payload = {
        "type": "callback",
        "merchant_id": "M1",
        "transaction_id": "T100",
        "status": "invalid_status",  # Should be success/failure/pending
        "provider_id": "P1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhooks/transaction", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_backpressure():
    """Endpoint returns 503 when event queue is full."""
    payload = {
        "type": "transaction",
        "merchant_id": "M1",
        "transaction_id": "T100",
        "amount": 100.50,
        "currency": "USD",
        "provider_id": "P1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Mock event_bus.enqueue to return False (queue full)
    with patch("hybrid_sentinel.routes.webhooks.event_bus") as mock_bus:
        mock_bus.enqueue = AsyncMock(return_value=False)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/webhooks/transaction", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"] == {"status": "overloaded"}
