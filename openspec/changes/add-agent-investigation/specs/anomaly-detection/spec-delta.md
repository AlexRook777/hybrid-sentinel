## MODIFIED Requirements

### Requirement: Anomaly Threshold Gating
WHEN the anomaly scorer has completed warmup and an event is scored,
the system SHALL emit an AnomalyEvent only if the score is greater than or equal to the configured `anomaly_threshold` (default 0.85).
WHEN an AnomalyEvent is emitted (score >= threshold or DRIFT type),
the system SHALL also publish it to the investigation bus for agent consumption.

#### Scenario: Below-threshold event is not emitted
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of 0.60
- **THEN** no AnomalyEvent is emitted
- **AND** nothing is published to the investigation bus

#### Scenario: Above-threshold event is emitted and forwarded
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of 0.92
- **THEN** an AnomalyEvent is emitted with `anomaly_score` set to 0.92
- **AND** the AnomalyEvent is published to the investigation bus

#### Scenario: Exact-threshold event is emitted and forwarded
- **GIVEN** the scorer is past warmup
- **WHEN** an event receives an anomaly score of exactly 0.85
- **THEN** an AnomalyEvent is emitted with `anomaly_score` set to 0.85
- **AND** the AnomalyEvent is published to the investigation bus

#### Scenario: DRIFT event is forwarded to investigation bus
- **GIVEN** a DRIFT AnomalyEvent is emitted by the scorer
- **WHEN** the event is processed
- **THEN** the DRIFT AnomalyEvent is published to the investigation bus

#### Scenario: Investigation bus full does not affect scoring
- **GIVEN** the investigation bus queue is at capacity
- **WHEN** the scorer emits an AnomalyEvent
- **THEN** the AnomalyEvent is still collected in the scored anomalies list
- **AND** a warning is logged that the investigation bus dropped the event
- **AND** the scorer continues processing without blocking
