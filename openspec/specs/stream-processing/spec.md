# Stream Processing

## ADDED Requirements

### Requirement: Transaction Event Data Model
WHEN a transaction event is received,
the system SHALL validate it against a schema requiring `merchant_id`, `transaction_id`, `amount`, `currency`, `provider_id`, `timestamp`, and `type` fields.

#### Scenario: Valid transaction event is accepted
- **WHEN** a JSON payload with all required fields and `type` set to `"transaction"` is submitted
- **THEN** the event is parsed into a `TransactionEvent` model without errors
- **AND** the `merchant_id` and `transaction_id` fields are non-empty strings

#### Scenario: Invalid transaction event is rejected
- **WHEN** a JSON payload is missing the `transaction_id` field
- **THEN** a validation error is raised
- **AND** the event is not forwarded to the stream processor

### Requirement: Callback Event Data Model
WHEN a callback event is received,
the system SHALL validate it against a schema requiring `merchant_id`, `transaction_id`, `status`, `actual_amount`, `actual_currency`, `provider_id`, `timestamp`, and `type` fields.

#### Scenario: Valid callback event is accepted
- **WHEN** a JSON payload with all required fields and `type` set to `"callback"` is submitted
- **THEN** the event is parsed into a `CallbackEvent` model without errors
- **AND** the `status` field is one of `"success"`, `"failure"`, or `"pending"`
- **AND** the `actual_amount` is a positive decimal value
- **AND** the `actual_currency` is exactly 3 characters

#### Scenario: Invalid callback event is rejected (unrecognized status)
- **WHEN** a JSON payload has an unrecognized `status` value
- **THEN** a validation error is raised

#### Scenario: Callback event missing actual_amount is rejected
- **WHEN** a JSON payload omits the `actual_amount` field
- **THEN** a validation error is raised
- **AND** the event is not forwarded to the stream processor

#### Scenario: Callback event missing actual_currency is rejected
- **WHEN** a JSON payload omits the `actual_currency` field
- **THEN** a validation error is raised
- **AND** the event is not forwarded to the stream processor

#### Scenario: Invalid actual_currency length is rejected
- **WHEN** a JSON payload has `actual_currency` with length != 3
- **THEN** a validation error is raised

### Requirement: Stateful Callback Matching
WHEN a transaction event arrives,
the system SHALL store it in keyed state indexed by `{merchant_id}:{transaction_id}` and wait for a matching callback.

#### Scenario: Callback arrives and matches a pending transaction
- **GIVEN** a transaction event with `merchant_id` "M1" and `transaction_id` "T100" is in state
- **WHEN** a callback event with the same `merchant_id` and `transaction_id` arrives
- **THEN** the system emits a matched pair event containing the transaction and callback data
- **AND** the entry is removed from state

#### Scenario: Callback arrives with no matching transaction
- **GIVEN** no transaction event with `merchant_id` "M1" and `transaction_id` "T999" is in state
- **WHEN** a callback event with `merchant_id` "M1" and `transaction_id` "T999" arrives
- **THEN** the system logs a warning for the orphaned callback
- **AND** no matched pair is emitted

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

### Requirement: Bytewax Dataflow Lifecycle
WHEN the application starts,
the system SHALL initialize and run the Bytewax dataflow in a background thread.

#### Scenario: Dataflow starts with application
- **GIVEN** the FastAPI application is starting via its lifespan handler
- **WHEN** the lifespan startup completes
- **THEN** the Bytewax dataflow thread is running
- **AND** the dataflow is consuming events from the input queue

#### Scenario: Dataflow stops with application
- **GIVEN** the Bytewax dataflow is running
- **WHEN** the FastAPI application shuts down
- **THEN** the dataflow thread is signaled to stop
- **AND** the thread joins within a reasonable timeout

### Requirement: Event Bus
WHEN an event is received by the webhook endpoint,
the system SHALL forward it to the Bytewax dataflow via an in-process event bus.

#### Scenario: Event is enqueued successfully
- **GIVEN** the event bus queue has capacity
- **WHEN** a valid event is submitted to the bus
- **THEN** the event is placed on the queue
- **AND** the webhook returns a success response

#### Scenario: Event bus is full (backpressure)
- **GIVEN** the event bus queue has reached its maximum size
- **WHEN** a new event is submitted to the bus
- **THEN** the webhook returns HTTP 503 Service Unavailable
- **AND** the event is not silently dropped

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
