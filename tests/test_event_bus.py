"""Unit tests for event bus."""

import asyncio

import pytest

from hybrid_sentinel.event_bus import EventBus


@pytest.mark.asyncio
async def test_enqueue_success():
    """Event is successfully enqueued when queue has capacity."""
    bus = EventBus(max_size=10)
    result = await bus.enqueue({"event": "test"})
    assert result is True
    assert bus.qsize() == 1


@pytest.mark.asyncio
async def test_enqueue_backpressure():
    """Enqueue returns False when queue is full."""
    bus = EventBus(max_size=2)

    # Fill the queue
    await bus.enqueue({"event": "1"})
    await bus.enqueue({"event": "2"})

    # Next enqueue should fail (backpressure)
    result = await bus.enqueue({"event": "3"})
    assert result is False
    assert bus.qsize() == 2


@pytest.mark.asyncio
async def test_is_full():
    """is_full returns True when queue reaches max capacity."""
    bus = EventBus(max_size=2)
    assert bus.is_full() is False

    await bus.enqueue({"event": "1"})
    assert bus.is_full() is False

    await bus.enqueue({"event": "2"})
    assert bus.is_full() is True


@pytest.mark.asyncio
async def test_dequeue():
    """Event can be dequeued from the queue."""
    bus = EventBus(max_size=10)
    event = {"event": "test"}
    await bus.enqueue(event)

    dequeued = await bus.dequeue()
    assert dequeued == event
    assert bus.qsize() == 0


@pytest.mark.asyncio
async def test_dequeue_timeout():
    """Dequeue returns None after timeout when queue is empty."""
    bus = EventBus(max_size=10)

    # Should timeout quickly since queue is empty
    dequeued = await bus.dequeue()
    assert dequeued is None


@pytest.mark.asyncio
async def test_enqueue_after_stop():
    """Enqueue returns False after bus is stopped."""
    bus = EventBus(max_size=10)
    bus.stop()

    result = await bus.enqueue({"event": "test"})
    assert result is False
