"""Per-merchant concept drift detection using River ADWIN."""

from dataclasses import dataclass

from river import drift


@dataclass
class DriftAlert:
    """Drift alert notification."""

    merchant_id: str
    metric_name: str  # "failure_rate" or "callback_latency"


class DriftDetectorManager:
    """Manages per-merchant ADWIN drift detectors for failure rate and callback latency."""

    def __init__(self) -> None:
        """Initialize drift detector manager."""
        # Per-merchant ADWIN instances: {merchant_id: {"failure_rate": ADWIN, "callback_latency": ADWIN}}
        self._detectors: dict[str, dict[str, drift.ADWIN]] = {}

    def update(
        self, merchant_id: str, is_failure: bool, latency: float
    ) -> list[DriftAlert]:
        """Update drift detectors for a merchant and return drift alerts if triggered.

        Args:
            merchant_id: Merchant identifier
            is_failure: Whether the callback was a failure (True) or success (False)
            latency: Callback latency in seconds

        Returns:
            List of DriftAlert if drift is detected, empty list otherwise
        """
        # Initialize detectors for this merchant if not exists
        if merchant_id not in self._detectors:
            self._detectors[merchant_id] = {
                "failure_rate": drift.ADWIN(),
                "callback_latency": drift.ADWIN(),
            }

        alerts: list[DriftAlert] = []

        # Update failure rate detector (binary: 1.0 for failure, 0.0 for success)
        failure_value = 1.0 if is_failure else 0.0
        self._detectors[merchant_id]["failure_rate"].update(failure_value)
        if self._detectors[merchant_id]["failure_rate"].drift_detected:
            alerts.append(DriftAlert(merchant_id=merchant_id, metric_name="failure_rate"))

        # Update callback latency detector
        self._detectors[merchant_id]["callback_latency"].update(latency)
        if self._detectors[merchant_id]["callback_latency"].drift_detected:
            alerts.append(
                DriftAlert(merchant_id=merchant_id, metric_name="callback_latency")
            )

        return alerts

    def get_detector_count(self) -> int:
        """Return the number of merchants being tracked."""
        return len(self._detectors)
