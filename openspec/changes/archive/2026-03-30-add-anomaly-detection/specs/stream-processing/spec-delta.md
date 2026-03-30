## MODIFIED Requirements

### Requirement: Timeout Anomaly Detection
WHEN a transaction has been in state for longer than the configured callback timeout (default 300 seconds),
the system SHALL emit a TIMEOUT anomaly event.

#### Scenario: Transaction times out without callback
- **GIVEN** a transaction event with `merchant_id` "M1" and `transaction_id` "T200" was received 300+ seconds ago
- **WHEN** the periodic timeout check executes
- **THEN** the system emits an `AnomalyEvent` with `anomaly_type` set to `"TIMEOUT"`
- **AND** the event includes the original transaction's `merchant_id`, `transaction_id`, and `provider_id`
- **AND** the timed-out entry is removed from state

#### Scenario: Transaction receives callback before timeout
- **GIVEN** a transaction event was received 60 seconds ago
- **WHEN** a matching callback arrives
- **THEN** no TIMEOUT anomaly event is emitted
- **AND** the matched pair is emitted normally

## ADDED Requirements

### Requirement: Scoring Bus Publication
WHEN the Bytewax sink outputs a MatchedPair or AnomalyEvent,
the system SHALL publish the event to the scoring bus in addition to collecting it in the existing in-memory lists.

#### Scenario: MatchedPair published to scoring bus
- **GIVEN** the scoring bus is available and has capacity
- **WHEN** a MatchedPair is written to the sink
- **THEN** the MatchedPair is appended to the `matched_pairs` list
- **AND** the MatchedPair is enqueued on the scoring bus

#### Scenario: AnomalyEvent published to scoring bus
- **GIVEN** the scoring bus is available and has capacity
- **WHEN** an AnomalyEvent is written to the sink
- **THEN** the AnomalyEvent is appended to the `anomaly_events` list
- **AND** the AnomalyEvent is enqueued on the scoring bus

#### Scenario: Scoring bus full does not block stream
- **GIVEN** the scoring bus queue is at capacity
- **WHEN** the sink attempts to publish an event
- **THEN** the event is still collected in the in-memory list
- **AND** a warning is logged that the scoring bus dropped the event
- **AND** the Bytewax dataflow continues without blocking

### Requirement: Extended AnomalyEvent Model
The AnomalyEvent model SHALL include an optional `anomaly_score` field of type float.

#### Scenario: Phase 1 TIMEOUT events have no score
- **WHEN** a TIMEOUT AnomalyEvent is emitted by the stream processor
- **THEN** `anomaly_score` is None (not set)

#### Scenario: Phase 2 scored events include score
- **WHEN** the anomaly scorer emits an AnomalyEvent
- **THEN** `anomaly_score` is a float between 0.0 and 1.0
