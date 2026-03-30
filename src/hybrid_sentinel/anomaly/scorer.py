"""Anomaly scorer using River online ML."""

import logging
import threading
from datetime import UTC, datetime

from river import anomaly

from hybrid_sentinel.agent import investigation_bus
from hybrid_sentinel.anomaly.classify import classify_anomaly
from hybrid_sentinel.anomaly.drift import DriftDetectorManager
from hybrid_sentinel.anomaly.features import extract_features
from hybrid_sentinel.config import settings
from hybrid_sentinel.models import AnomalyEvent, MatchedPair

logger = logging.getLogger(__name__)


class AnomalyScorer:
    """Online anomaly scorer using River HalfSpaceTrees with ADWIN drift detection."""

    def __init__(self) -> None:
        """Initialize anomaly scorer."""
        # River HalfSpaceTrees model
        self._model = anomaly.HalfSpaceTrees(
            n_trees=settings.hst_n_trees,
            height=settings.hst_height,
            window_size=settings.hst_window_size,
            seed=42,
        )

        # Drift detection
        self._drift_manager = DriftDetectorManager()

        # Warmup tracking
        self._events_processed = 0
        self._warmup_target = settings.model_warmup_events
        self._is_warmed_up = False

        # Anomaly collection (thread-safe)
        self._lock = threading.Lock()
        self._scored_anomalies: list[AnomalyEvent] = []

        # Rolling latency tracking for LATENCY_SPIKE classification
        self._latency_sum = 0.0
        self._latency_count = 0
        self._rolling_latency_mean = 0.0

        # Thread control
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, scoring_bus) -> None:
        """Start the scorer in a background thread.

        Args:
            scoring_bus: EventBus instance to consume from
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, args=(scoring_bus,), daemon=True
        )
        self._thread.start()
        logger.info("Anomaly scorer started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the scorer thread.

        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join(timeout=timeout)
        logger.info("Anomaly scorer stopped")

    def _run_loop(self, scoring_bus) -> None:
        """Main scoring loop (runs in background thread)."""
        while not self._stop_event.is_set():
            event = scoring_bus.dequeue(timeout=0.5)
            if event is not None:
                self.score_event(event)

    def score_event(self, event: MatchedPair | AnomalyEvent) -> None:
        """Score an event and emit AnomalyEvent if threshold exceeded.

        Args:
            event: MatchedPair or AnomalyEvent to score
        """
        # Extract features
        features = extract_features(event)

        # Score with River model
        score = self._model.score_one(features)

        # Learn from observation (always, regardless of warmup)
        self._model.learn_one(features)

        # Update warmup counter
        self._events_processed += 1
        if not self._is_warmed_up and self._events_processed >= self._warmup_target:
            self._is_warmed_up = True
            logger.info(
                "Anomaly scorer warmup complete (%d events)", self._events_processed
            )

        # Update rolling latency mean (for LATENCY_SPIKE classification)
        # Use raw (unnormalized) latency for meaningful comparison
        if isinstance(event, MatchedPair):
            latency_raw = features["callback_latency_s_raw"]
            self._latency_sum += latency_raw
            self._latency_count += 1
            self._rolling_latency_mean = self._latency_sum / self._latency_count

        # Drift detection (independent of warmup)
        if isinstance(event, MatchedPair) and settings.drift_detection_enabled:
            is_failure = event.callback.status == "failure"
            latency_raw = features["callback_latency_s_raw"]
            drift_alerts = self._drift_manager.update(
                merchant_id=event.transaction.merchant_id,
                is_failure=is_failure,
                latency=latency_raw,
            )

            # Emit DRIFT anomaly events
            for alert in drift_alerts:
                drift_event = AnomalyEvent(
                    anomaly_type="DRIFT",
                    merchant_id=alert.merchant_id,
                    transaction_id=event.transaction.transaction_id,
                    provider_id=event.transaction.provider_id,
                    timestamp=datetime.now(UTC),
                    details={
                        "drift_metric": alert.metric_name,
                        "merchant_id": alert.merchant_id,
                    },
                    anomaly_score=None,  # Drift is deterministic, not ML-scored
                )
                with self._lock:
                    self._scored_anomalies.append(drift_event)
                if not investigation_bus.enqueue(drift_event):
                    logger.warning(
                        "Investigation bus full, dropped DRIFT event: %s",
                        alert.merchant_id,
                    )
                logger.warning(
                    "Drift detected: %s - %s metric",
                    alert.merchant_id,
                    alert.metric_name,
                )

        # Emit scored anomaly if past warmup and above threshold
        if self._is_warmed_up and score >= settings.anomaly_threshold:
            # Classify anomaly type
            anomaly_type = classify_anomaly(
                event, features, score, self._rolling_latency_mean
            )

            # Create scored AnomalyEvent
            if isinstance(event, MatchedPair):
                scored_event = AnomalyEvent(
                    anomaly_type=anomaly_type,
                    merchant_id=event.transaction.merchant_id,
                    transaction_id=event.transaction.transaction_id,
                    provider_id=event.transaction.provider_id,
                    timestamp=event.match_timestamp,
                    anomaly_score=score,
                )
            else:  # AnomalyEvent (TIMEOUT)
                scored_event = AnomalyEvent(
                    anomaly_type=anomaly_type,
                    merchant_id=event.merchant_id,
                    transaction_id=event.transaction_id,
                    provider_id=event.provider_id,
                    timestamp=event.timestamp,
                    anomaly_score=score,
                )

            with self._lock:
                self._scored_anomalies.append(scored_event)
            if not investigation_bus.enqueue(scored_event):
                logger.warning(
                    "Investigation bus full, dropped event: %s:%s",
                    scored_event.merchant_id,
                    scored_event.transaction_id,
                )

            logger.warning(
                "Anomaly scored: type=%s score=%.3f merchant=%s txn=%s",
                anomaly_type,
                score,
                scored_event.merchant_id,
                scored_event.transaction_id,
            )

    def get_scored_anomalies(self) -> list[AnomalyEvent]:
        """Return copy of scored anomalies list (thread-safe)."""
        with self._lock:
            return self._scored_anomalies.copy()

    def get_stats(self) -> dict:
        """Return scorer statistics.

        Returns:
            Dictionary with warmup status, events processed, anomalies emitted, etc.
        """
        with self._lock:
            anomalies_emitted = len(self._scored_anomalies)

        return {
            "is_warmed_up": self._is_warmed_up,
            "events_processed": self._events_processed,
            "warmup_target": self._warmup_target,
            "anomalies_emitted": anomalies_emitted,
            "drift_detectors_active": self._drift_manager.get_detector_count(),
        }
