"""Bytewax output sink for matched pairs and anomaly events."""

import logging
from collections.abc import Iterable

from bytewax.outputs import DynamicSink, StatelessSinkPartition

from hybrid_sentinel.models import AnomalyEvent, MatchedPair

logger = logging.getLogger(__name__)


# In-process collection for Phase 1
# Phase 2 (River) will replace this with its scoring pipeline
matched_pairs: list[MatchedPair] = []
anomaly_events: list[AnomalyEvent] = []


class EventCollectorPartition(StatelessSinkPartition):
    """Sink partition that collects matched pairs and anomaly events."""

    def write_batch(self, batch: Iterable) -> None:
        """Write a batch of events to the appropriate collection.

        Args:
            batch: List of MatchedPair or AnomalyEvent objects.
        """
        for item in batch:
            if isinstance(item, MatchedPair):
                matched_pairs.append(item)
                logger.info(
                    "Matched pair: %s:%s",
                    item.transaction.merchant_id,
                    item.transaction.transaction_id,
                )
            elif isinstance(item, AnomalyEvent):
                anomaly_events.append(item)
                logger.warning(
                    "Anomaly: %s - %s:%s",
                    item.anomaly_type,
                    item.merchant_id,
                    item.transaction_id,
                )


class EventCollectorSink(DynamicSink):
    """Bytewax sink for collecting matched pairs and anomaly events."""

    def build(
        self, step_id: str, worker_index: int, worker_count: int
    ) -> EventCollectorPartition:
        """Build a sink partition for the given worker."""
        return EventCollectorPartition()
