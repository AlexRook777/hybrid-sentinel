"""In-process event bus for connecting FastAPI to Bytewax dataflow."""

import asyncio
from typing import Any

from hybrid_sentinel.config import settings


class EventBus:
    """Asyncio Queue-based event bus with backpressure support."""

    def __init__(self, max_size: int | None = None):
        """Initialize event bus with configurable queue size.

        Args:
            max_size: Maximum queue size. Defaults to settings.queue_max_size.
        """
        self._max_size = max_size or settings.queue_max_size
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._max_size)
        self._stopped = False

    async def enqueue(self, event: Any) -> bool:
        """Enqueue an event.

        Args:
            event: Event to enqueue.

        Returns:
            True if enqueued successfully, False if queue is full.
        """
        if self._stopped:
            return False

        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            return False

    async def dequeue(self) -> Any | None:
        """Dequeue an event (blocking).

        Returns:
            Event or None if bus is stopped and queue is empty.
        """
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except TimeoutError:
            return None

    def stop(self) -> None:
        """Signal that the bus is stopping."""
        self._stopped = True

    def is_full(self) -> bool:
        """Check if the queue is full."""
        return self._queue.full()

    def qsize(self) -> int:
        """Return the approximate size of the queue."""
        return self._queue.qsize()


# Global event bus instance
event_bus = EventBus()
