"""In-process event bus for connecting FastAPI to Bytewax dataflow."""

import queue

from hybrid_sentinel.config import settings


class EventBus:
    """Thread-safe queue-based event bus with backpressure support."""

    def __init__(self, max_size: int | None = None) -> None:
        self._max_size = max_size or settings.queue_max_size
        self._queue: queue.Queue[object] = queue.Queue(maxsize=self._max_size)
        self._stopped = False

    def enqueue(self, event: object) -> bool:
        """Enqueue an event (non-blocking).

        Returns:
            True if enqueued successfully, False if queue is full or bus is stopped.
        """
        if self._stopped:
            return False
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            return False

    def dequeue(self, timeout: float = 1.0) -> object | None:
        """Dequeue an event with timeout.

        Returns:
            Event or None if timeout expires.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def dequeue_nowait(self) -> object | None:
        """Dequeue an event without blocking.

        Returns:
            Event or None if queue is empty.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        """Signal that the bus is stopping."""
        self._stopped = True

    def reset(self) -> None:
        """Reset the bus for reuse (e.g. between tests)."""
        self._stopped = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @property
    def stopped(self) -> bool:
        """Whether the bus has been stopped."""
        return self._stopped

    def is_full(self) -> bool:
        """Check if the queue is full."""
        return self._queue.full()

    def qsize(self) -> int:
        """Return the approximate size of the queue."""
        return self._queue.qsize()


# Global event bus instance
event_bus = EventBus()
