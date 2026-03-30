"""Bytewax source that reads from the event bus queue."""

from typing import Any

from bytewax.inputs import FixedPartitionedSource, StatefulSourcePartition

from hybrid_sentinel.event_bus import event_bus


class EventQueueSourcePartition(StatefulSourcePartition[Any, None]):
    """Source partition that reads from the thread-safe event bus queue."""

    def next_batch(self) -> list[Any]:
        """Return the next batch of events from the queue.

        Blocks up to 0.5 s for the first item, then drains up to 99 more
        non-blocking.  Raises StopIteration when the bus is stopped so
        Bytewax can shut down the dataflow cleanly.
        """
        if event_bus.stopped:
            raise StopIteration

        batch: list[Any] = []
        item = event_bus.dequeue(timeout=0.5)
        if item is not None:
            batch.append(item)
            for _ in range(99):
                item = event_bus.dequeue_nowait()
                if item is None:
                    break
                batch.append(item)
        return batch

    def snapshot(self) -> None:
        return None


class EventQueueSource(FixedPartitionedSource[Any, None]):
    """Bytewax source for reading events from the event bus queue."""

    def list_parts(self) -> list[str]:
        return ["singleton"]

    def build_part(
        self, step_id: str, for_key: str, _resume_state: None
    ) -> EventQueueSourcePartition:
        return EventQueueSourcePartition()
