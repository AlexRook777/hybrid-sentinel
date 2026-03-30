"""Bytewax output sink for matched pairs and anomaly events."""

import logging
import threading
from collections.abc import Iterable

from bytewax.outputs import DynamicSink, StatelessSinkPartition

from hybrid_sentinel.anomaly import scoring_bus
from hybrid_sentinel.models import AnomalyEvent, MatchedPair

logger = logging.getLogger(__name__)

# Thread-safe in-process collection for Phase 1.
# Phase 2 (River) will replace this with its scoring pipeline.
_sink_lock = threading.Lock()
matched_pairs: list[MatchedPair] = []
anomaly_events: list[AnomalyEvent] = []


class EventCollectorPartition(StatelessSinkPartition):
    """Sink partition that collects matched pairs and anomaly events."""

    def write_batch(self, batch: Iterable) -> None:
        for item in batch:
            if isinstance(item, MatchedPair):
                with _sink_lock:
                    matched_pairs.append(item)
                logger.info(
                    "Matched pair: %s:%s",
                    item.transaction.merchant_id,
                    item.transaction.transaction_id,
                )
                # Publish to scoring bus (non-blocking)
                if not scoring_bus.enqueue(item):
                    logger.warning(
                        "Scoring bus full, dropped MatchedPair: %s:%s",
                        item.transaction.merchant_id,
                        item.transaction.transaction_id,
                    )
            elif isinstance(item, AnomalyEvent):
                with _sink_lock:
                    anomaly_events.append(item)
                logger.warning(
                    "Anomaly: %s - %s:%s",
                    item.anomaly_type,
                    item.merchant_id,
                    item.transaction_id,
                )
                # Publish to scoring bus (non-blocking)
                if not scoring_bus.enqueue(item):
                    logger.warning(
                        "Scoring bus full, dropped AnomalyEvent: %s:%s",
                        item.merchant_id,
                        item.transaction_id,
                    )


class EventCollectorSink(DynamicSink):
    """Bytewax sink for collecting matched pairs and anomaly events."""

    def build(
        self, step_id: str, worker_index: int, worker_count: int
    ) -> EventCollectorPartition:
        return EventCollectorPartition()
