"""Unit tests for event bus."""

from hybrid_sentinel.event_bus import EventBus


def test_enqueue_success():
    """Event is successfully enqueued when queue has capacity."""
    bus = EventBus(max_size=10)
    result = bus.enqueue({"event": "test"})
    assert result is True
    assert bus.qsize() == 1


def test_enqueue_backpressure():
    """Enqueue returns False when queue is full."""
    bus = EventBus(max_size=2)

    bus.enqueue({"event": "1"})
    bus.enqueue({"event": "2"})

    result = bus.enqueue({"event": "3"})
    assert result is False
    assert bus.qsize() == 2


def test_is_full():
    """is_full returns True when queue reaches max capacity."""
    bus = EventBus(max_size=2)
    assert bus.is_full() is False

    bus.enqueue({"event": "1"})
    assert bus.is_full() is False

    bus.enqueue({"event": "2"})
    assert bus.is_full() is True


def test_dequeue():
    """Event can be dequeued from the queue."""
    bus = EventBus(max_size=10)
    event = {"event": "test"}
    bus.enqueue(event)

    dequeued = bus.dequeue()
    assert dequeued == event
    assert bus.qsize() == 0


def test_dequeue_timeout():
    """Dequeue returns None after timeout when queue is empty."""
    bus = EventBus(max_size=10)
    dequeued = bus.dequeue(timeout=0.1)
    assert dequeued is None


def test_dequeue_nowait_empty():
    """dequeue_nowait returns None when queue is empty."""
    bus = EventBus(max_size=10)
    assert bus.dequeue_nowait() is None


def test_enqueue_after_stop():
    """Enqueue returns False after bus is stopped."""
    bus = EventBus(max_size=10)
    bus.stop()

    result = bus.enqueue({"event": "test"})
    assert result is False


def test_reset():
    """Bus can be reset and reused after stopping."""
    bus = EventBus(max_size=10)
    bus.enqueue({"event": "1"})
    bus.stop()
    assert bus.enqueue({"event": "2"}) is False

    bus.reset()
    assert bus.stopped is False
    assert bus.qsize() == 0
    assert bus.enqueue({"event": "3"}) is True
