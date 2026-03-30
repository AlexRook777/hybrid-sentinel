## ADDED Requirements

### Requirement: Feature Extraction
WHEN a MatchedPair or TIMEOUT AnomalyEvent is received by the anomaly scorer,
the system SHALL extract a feature vector as a dictionary of string keys to float values containing at minimum: `amount_log`, `callback_latency_s`, `is_success`, `is_failure`, `is_amount_mismatch`, `amount_mismatch_pct`, `hour_of_day`, `day_of_week`, `is_round_amount`, `provider_hash`, `merchant_hash`, and `is_timeout`.

#### Scenario: Feature extraction from a MatchedPair
- **GIVEN** a MatchedPair with transaction amount 500.00, callback status "success", callback latency 2.5 seconds, and no amount mismatch
- **WHEN** features are extracted
- **THEN** the result is a dict with `amount_log` approximately 6.21, `callback_latency_s` equal to 2.5, `is_success` equal to 1.0, `is_failure` equal to 0.0, `is_amount_mismatch` equal to 0.0, `amount_mismatch_pct` equal to 0.0, and `is_timeout` equal to 0.0

#### Scenario: Feature extraction from a TIMEOUT AnomalyEvent
- **GIVEN** an AnomalyEvent with `anomaly_type` "TIMEOUT" and transaction amount 100.00
- **WHEN** features are extracted
- **THEN** `callback_latency_s` is set to 300.0 (the timeout threshold), `is_success` is 0.0, `is_failure` is 0.0, `is_timeout` is 1.0, and `amount_mismatch_pct` is 0.0

#### Scenario: Temporal features are normalized
- **WHEN** features are extracted from an event with timestamp at 15:00 on a Wednesday
- **THEN** `hour_of_day` is approximately 0.625 (15/24) and `day_of_week` is approximately 0.429 (3/7)

### Requirement: Anomaly Scoring with HalfSpaceTrees
WHEN a feature vector is submitted to the anomaly model,
the system SHALL produce an anomaly score in the range [0.0, 1.0] using River's HalfSpaceTrees algorithm and incrementally update the model with the observation.

#### Scenario: Normal transaction receives low score
- **GIVEN** the model has been warmed up with 1000+ typical transactions
- **WHEN** a feature vector representing a normal transaction is scored
- **THEN** the anomaly score is below 0.85

#### Scenario: Anomalous transaction receives high score
- **GIVEN** the model has been warmed up with 1000+ typical transactions
- **WHEN** a feature vector with extreme values (e.g., amount 100x the mean, latency 50x the mean) is scored
- **THEN** the anomaly score is at or above 0.85

#### Scenario: Model updates incrementally
- **WHEN** a feature vector is scored
- **THEN** the model updates its internal state with the new observation
- **AND** subsequent scores reflect the learned distribution including this observation

### Requirement: Silent Warmup Period
WHEN the anomaly scorer has processed fewer than the configured `model_warmup_events` (default 1000),
the system SHALL NOT emit any scored AnomalyEvents.

#### Scenario: No anomaly events during warmup
- **GIVEN** the scorer has processed 500 events and `model_warmup_events` is 1000
- **WHEN** an event with a high anomaly score is processed
- **THEN** no AnomalyEvent is emitted
- **AND** the model still learns from the observation

#### Scenario: Anomaly events emitted after warmup
- **GIVEN** the scorer has processed 1001 events and `model_warmup_events` is 1000
- **WHEN** an event with anomaly score ≥ 0.85 is processed
- **THEN** a scored AnomalyEvent is emitted with the `anomaly_score` field populated

#### Scenario: TIMEOUT passthrough during warmup
- **GIVEN** the scorer is in warmup mode
- **WHEN** a TIMEOUT AnomalyEvent arrives from Phase 1
- **THEN** the TIMEOUT event is logged but no scored AnomalyEvent is emitted
- **AND** the model learns from the TIMEOUT's features

### Requirement: Anomaly Threshold Gating
WHEN the anomaly scorer has completed warmup and an event is scored,
the system SHALL emit an AnomalyEvent only if the score is greater than or equal to the configured `anomaly_threshold` (default 0.85).

#### Scenario: Below-threshold event is not emitted
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of 0.60
- **THEN** no AnomalyEvent is emitted

#### Scenario: Above-threshold event is emitted
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of 0.92
- **THEN** an AnomalyEvent is emitted with `anomaly_score` set to 0.92

#### Scenario: Exact-threshold event is emitted
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of exactly 0.85
- **THEN** an AnomalyEvent is emitted with `anomaly_score` set to 0.85

### Requirement: Anomaly Type Classification
WHEN a scored event exceeds the anomaly threshold,
the system SHALL classify it into one of the following types based on feature analysis: `TIMEOUT`, `AMOUNT_MISMATCH`, `LATENCY_SPIKE`, `DRIFT`, or `BEHAVIORAL`.

#### Scenario: TIMEOUT event is classified as TIMEOUT
- **GIVEN** the source event was a Phase 1 TIMEOUT AnomalyEvent
- **WHEN** it scores above the threshold
- **THEN** the emitted AnomalyEvent has `anomaly_type` set to `"TIMEOUT"`

#### Scenario: Amount mismatch is classified as AMOUNT_MISMATCH
- **GIVEN** a MatchedPair where `amount_mismatch_pct` exceeds 10%
- **WHEN** it scores above the threshold
- **THEN** the emitted AnomalyEvent has `anomaly_type` set to `"AMOUNT_MISMATCH"`

#### Scenario: Latency spike is classified as LATENCY_SPIKE
- **GIVEN** a MatchedPair where `callback_latency_s` exceeds 3 times the rolling mean latency
- **WHEN** it scores above the threshold
- **THEN** the emitted AnomalyEvent has `anomaly_type` set to `"LATENCY_SPIKE"`

#### Scenario: Unclassified anomaly defaults to BEHAVIORAL
- **GIVEN** a scored event exceeds the threshold but matches no specific sub-type
- **WHEN** classification is performed
- **THEN** the emitted AnomalyEvent has `anomaly_type` set to `"BEHAVIORAL"`

### Requirement: Concept Drift Detection (ADWIN)
WHEN a MatchedPair event is processed,
the system SHALL update per-merchant ADWIN drift detectors for failure rate and callback latency, and emit a DRIFT AnomalyEvent when a statistically significant shift is detected.

#### Scenario: Drift detected in failure rate
- **GIVEN** merchant "M1" historically has a 2% failure rate
- **WHEN** merchant "M1" failure rate shifts to 15% and ADWIN detects the change
- **THEN** a DRIFT AnomalyEvent is emitted with `merchant_id` "M1"
- **AND** `details` includes `{"drift_metric": "failure_rate", "merchant_id": "M1"}`

#### Scenario: Drift detected in callback latency
- **GIVEN** merchant "M2" historically has mean callback latency of 1.5 seconds
- **WHEN** merchant "M2" latency shifts to 8.0 seconds and ADWIN detects the change
- **THEN** a DRIFT AnomalyEvent is emitted with `merchant_id` "M2"
- **AND** `details` includes `{"drift_metric": "callback_latency", "merchant_id": "M2"}`

#### Scenario: No drift when behavior is stable
- **GIVEN** merchant "M3" has stable failure rate and latency
- **WHEN** events for "M3" are processed
- **THEN** no DRIFT AnomalyEvent is emitted for "M3"

#### Scenario: Drift detection is independent of warmup
- **GIVEN** the scorer is in warmup mode
- **WHEN** ADWIN detects drift for a merchant
- **THEN** a DRIFT AnomalyEvent is still emitted (drift is deterministic, not ML-dependent)

### Requirement: Scoring Bus Integration
WHEN the Bytewax sink outputs a MatchedPair or AnomalyEvent,
the system SHALL publish it to a scoring bus that the anomaly scorer consumes.

#### Scenario: MatchedPair is published to scoring bus
- **GIVEN** the Bytewax dataflow emits a MatchedPair
- **WHEN** the sink processes the output
- **THEN** the MatchedPair is published to the scoring bus
- **AND** the MatchedPair is still collected in the existing in-memory list

#### Scenario: TIMEOUT AnomalyEvent is published to scoring bus
- **GIVEN** the Bytewax dataflow emits a TIMEOUT AnomalyEvent
- **WHEN** the sink processes the output
- **THEN** the AnomalyEvent is published to the scoring bus

#### Scenario: Scoring bus backpressure
- **GIVEN** the scoring bus queue is full
- **WHEN** the sink attempts to publish an event
- **THEN** the event is logged as dropped
- **AND** the Bytewax pipeline is not blocked

### Requirement: Anomaly Scorer Lifecycle
WHEN the application starts,
the system SHALL initialize and run the anomaly scorer in a background thread alongside the Bytewax dataflow.

#### Scenario: Scorer starts with application
- **GIVEN** the FastAPI application is starting via its lifespan handler
- **WHEN** the lifespan startup completes
- **THEN** the anomaly scorer thread is running
- **AND** it is consuming from the scoring bus

#### Scenario: Scorer stops with application
- **GIVEN** the anomaly scorer is running
- **WHEN** the FastAPI application shuts down
- **THEN** the scorer thread is signaled to stop
- **AND** the thread joins within a reasonable timeout

### Requirement: Anomaly Detection Configuration
The system SHALL expose the following configurable settings for anomaly detection, loaded from environment variables with the `SENTINEL_` prefix.

#### Scenario: Default configuration values
- **WHEN** no environment variables are set for anomaly detection
- **THEN** `anomaly_threshold` defaults to 0.85
- **AND** `model_warmup_events` defaults to 1000
- **AND** `drift_detection_enabled` defaults to True
- **AND** `scoring_queue_max_size` defaults to 10000
- **AND** `hst_n_trees` defaults to 15
- **AND** `hst_height` defaults to 6
- **AND** `hst_window_size` defaults to 500

#### Scenario: Custom threshold via environment
- **GIVEN** the environment variable `SENTINEL_ANOMALY_THRESHOLD` is set to "0.90"
- **WHEN** the application starts
- **THEN** the anomaly threshold is 0.90

### Requirement: Anomaly Stats Endpoint
The system SHALL expose a `GET /anomalies/stats` endpoint that returns the current state of the anomaly scorer.

#### Scenario: Stats during warmup
- **GIVEN** the scorer has processed 400 of 1000 warmup events
- **WHEN** a GET request is made to `/anomalies/stats`
- **THEN** the response contains `{"is_warmed_up": false, "events_processed": 400, "warmup_target": 1000, "anomalies_emitted": 0, "drift_detectors_active": <count>}`

#### Scenario: Stats after warmup
- **GIVEN** the scorer is past warmup and has emitted 12 anomalies from 5000 events
- **WHEN** a GET request is made to `/anomalies/stats`
- **THEN** the response contains `{"is_warmed_up": true, "events_processed": 5000, "warmup_target": 1000, "anomalies_emitted": 12, "drift_detectors_active": <count>}`
