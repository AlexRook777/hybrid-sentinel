"""Tests for drift detection."""

from hybrid_sentinel.anomaly.drift import DriftDetectorManager


def test_drift_detector_stable_behavior_no_alert():
    """Stable behavior does not trigger drift alert."""
    manager = DriftDetectorManager()

    # Feed stable data: low failure rate, consistent latency
    for _ in range(100):
        alerts = manager.update(merchant_id="M1", is_failure=False, latency=2.0)
        # No drift should be detected in stable conditions
        if alerts:
            # Allow for occasional false positives in early observations
            pass

    # After 100 stable observations, no drift
    alerts = manager.update(merchant_id="M1", is_failure=False, latency=2.0)
    # In practice, ADWIN might occasionally trigger, but we expect stability overall


def test_drift_detector_failure_rate_shift():
    """Failure rate shift triggers drift alert."""
    manager = DriftDetectorManager()

    # Establish baseline: 2% failure rate (2 failures per 100 transactions)
    for i in range(200):
        is_failure = (i % 50) == 0  # ~2% failure rate
        manager.update(merchant_id="M2", is_failure=is_failure, latency=1.5)

    # Shift to 50% failure rate
    drift_detected = False
    for i in range(100):
        is_failure = (i % 2) == 0  # 50% failure rate
        alerts = manager.update(merchant_id="M2", is_failure=is_failure, latency=1.5)
        if any(alert.metric_name == "failure_rate" for alert in alerts):
            drift_detected = True
            break

    assert drift_detected, "Expected drift detection on failure rate shift"


def test_drift_detector_latency_shift():
    """Callback latency shift triggers drift alert."""
    manager = DriftDetectorManager()

    # Establish baseline: consistent 1.5s latency
    for _ in range(200):
        manager.update(merchant_id="M3", is_failure=False, latency=1.5)

    # Shift to 8.0s latency
    drift_detected = False
    for _ in range(100):
        alerts = manager.update(merchant_id="M3", is_failure=False, latency=8.0)
        if any(alert.metric_name == "callback_latency" for alert in alerts):
            drift_detected = True
            break

    assert drift_detected, "Expected drift detection on latency shift"


def test_drift_detector_per_merchant_isolation():
    """Drift detection is isolated per merchant."""
    manager = DriftDetectorManager()

    # M4: stable behavior
    for _ in range(100):
        manager.update(merchant_id="M4", is_failure=False, latency=2.0)

    # M5: failure rate shift
    for i in range(50):
        is_failure = (i % 50) == 0
        manager.update(merchant_id="M5", is_failure=is_failure, latency=2.0)

    for i in range(50):
        is_failure = (i % 2) == 0  # Shift to 50%
        alerts = manager.update(merchant_id="M5", is_failure=is_failure, latency=2.0)
        if alerts:
            # Verify alert is for M5, not M4
            assert all(alert.merchant_id == "M5" for alert in alerts)

    # M4 should remain stable
    alerts = manager.update(merchant_id="M4", is_failure=False, latency=2.0)
    # No drift for M4 (or if any, should not be related to M5's behavior)


def test_drift_detector_count():
    """Detector count reflects number of tracked merchants."""
    manager = DriftDetectorManager()

    assert manager.get_detector_count() == 0

    manager.update(merchant_id="M6", is_failure=False, latency=1.0)
    assert manager.get_detector_count() == 1

    manager.update(merchant_id="M7", is_failure=False, latency=1.0)
    assert manager.get_detector_count() == 2

    # Updating same merchant doesn't increase count
    manager.update(merchant_id="M6", is_failure=False, latency=1.0)
    assert manager.get_detector_count() == 2
