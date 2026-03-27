"""Bytewax source that reads from the event bus asyncio Queue."""

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

from bytewax.inputs import FixedPartitionedSource, StatefulSourcePartition, batch_async

from hybrid_sentinel.event_bus import event_bus


async def _event_queue_helper() -> AsyncIterator[Any]:
    """Async generator that reads from the event bus queue."""
    while True:
        event = await event_bus.dequeue()
        if event is not None:
            yield event


class EventQueueSourcePartition(StatefulSourcePartition[Any, None]):
    """Source partition that reads from the event bus queue."""

    def __init__(self) -> None:
        """Initialize the source partition with async queue reader."""
        agen = _event_queue_helper()
        # Batch events with 0.5s timeout or max 100 items per batch
        self._batcher = batch_async(agen, timedelta(seconds=0.5), 100)

    def next_batch(self) -> list[Any]:
        """Return the next batch of events from the queue."""
        return next(self._batcher)

    def snapshot(self) -> None:
        """Return snapshot state (not used for now)."""
        return None


class EventQueueSource(FixedPartitionedSource[Any, None]):
    """Bytewax source for reading events from the event bus queue."""

    def list_parts(self) -> list[str]:
        """Return list of partition keys (single partition for now)."""
        return ["singleton"]

    def build_part(
        self, step_id: str, for_key: str, _resume_state: None
    ) -> EventQueueSourcePartition:
        """Build a source partition for the given key."""
        return EventQueueSourcePartition()
