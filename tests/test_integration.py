"""Integration tests for stream processing pipeline."""

import asyncio
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from hybrid_sentinel.main import app
from hybrid_sentinel.stream.sink import anomaly_events, matched_pairs


@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E test - requires full dataflow running")
async def test_transaction_callback_matching():
    """Submit transaction and callback, verify matched pair is emitted."""
    # Clear any previous test data
    matched_pairs.clear()
    anomaly_events.clear()

    now = datetime.now(timezone.utc)
    merchant_id = "M_TEST_1"
    transaction_id = "T_MATCH_1"

    transaction_payload = {
        "type": "transaction",
        "merchant_id": merchant_id,
        "transaction_id": transaction_id,
        "amount": 100.0,
        "currency": "USD",
        "provider_id": "P1",
        "timestamp": now.isoformat(),
    }

    callback_payload = {
        "type": "callback",
        "merchant_id": merchant_id,
        "transaction_id": transaction_id,
        "status": "success",
        "provider_id": "P1",
        "timestamp": now.isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Submit transaction
        response1 = await client.post("/webhooks/transaction", json=transaction_payload)
        assert response1.status_code == 202

        # Submit callback
        response2 = await client.post("/webhooks/transaction", json=callback_payload)
        assert response2.status_code == 202

        # Wait for dataflow processing (give it a moment)
        await asyncio.sleep(2)

    # Verify matched pair was emitted
    assert len(matched_pairs) >= 1
    found = False
    for pair in matched_pairs:
        if (
            pair.transaction.merchant_id == merchant_id
            and pair.transaction.transaction_id == transaction_id
        ):
            assert pair.callback.status == "success"
            found = True
            break
    assert found, f"Matched pair not found for {merchant_id}:{transaction_id}"


@pytest.mark.asyncio
@pytest.mark.skip(reason="E2E test - requires full dataflow running")
async def test_timeout_anomaly_detection():
    """Submit transaction without callback, verify TIMEOUT anomaly is emitted.

    Note: This test uses a shortened timeout for faster execution.
    It overrides settings.callback_timeout temporarily.
    """
    # Clear any previous test data
    matched_pairs.clear()
    anomaly_events.clear()

    # Temporarily shorten timeout for testing (override in config)
    from hybrid_sentinel.config import settings

    original_timeout = settings.callback_timeout
    original_tick = settings.tick_interval
    settings.callback_timeout = 3  # 3 seconds for testing
    settings.tick_interval = 2  # 2 seconds tick interval

    try:
        now = datetime.now(timezone.utc)
        merchant_id = "M_TEST_2"
        transaction_id = "T_TIMEOUT_1"

        transaction_payload = {
            "type": "transaction",
            "merchant_id": merchant_id,
            "transaction_id": transaction_id,
            "amount": 200.0,
            "currency": "USD",
            "provider_id": "P2",
            "timestamp": now.isoformat(),
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Submit transaction only (no callback)
            response = await client.post("/webhooks/transaction", json=transaction_payload)
            assert response.status_code == 202

            # Wait longer than timeout + tick interval
            await asyncio.sleep(6)

        # Verify TIMEOUT anomaly was emitted
        # Note: This might be flaky in CI due to timing
        assert len(anomaly_events) >= 1
        found = False
        for anomaly in anomaly_events:
            if (
                anomaly.merchant_id == merchant_id
                and anomaly.transaction_id == transaction_id
                and anomaly.anomaly_type == "TIMEOUT"
            ):
                found = True
                break

        # If not found, it might be a timing issue - log for debugging
        if not found:
            print(f"Warning: TIMEOUT anomaly not detected (timing issue?). Anomalies: {len(anomaly_events)}")
        # For now, we'll assert to catch real issues, but this test might need adjustment
        assert found, f"TIMEOUT anomaly not found for {merchant_id}:{transaction_id}"

    finally:
        # Restore original settings
        settings.callback_timeout = original_timeout
        settings.tick_interval = original_tick
