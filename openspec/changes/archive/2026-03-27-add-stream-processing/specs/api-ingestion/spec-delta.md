## ADDED Requirements

### Requirement: Webhook Transaction Ingestion Endpoint
WHEN the system receives a POST request to `/webhooks/transaction`,
the system SHALL validate the payload and forward the event to the stream processor.

#### Scenario: Valid transaction event is ingested
- **WHEN** a POST request with a valid transaction JSON payload (`type: "transaction"`) is sent to `/webhooks/transaction`
- **THEN** the response status code is 202 Accepted
- **AND** the response body contains `{"status": "accepted"}`
- **AND** the event is forwarded to the stream processing pipeline

#### Scenario: Valid callback event is ingested
- **WHEN** a POST request with a valid callback JSON payload (`type: "callback"`) is sent to `/webhooks/transaction`
- **THEN** the response status code is 202 Accepted
- **AND** the response body contains `{"status": "accepted"}`
- **AND** the event is forwarded to the stream processing pipeline

#### Scenario: Invalid payload is rejected
- **WHEN** a POST request with an invalid or malformed JSON payload is sent to `/webhooks/transaction`
- **THEN** the response status code is 422 Unprocessable Entity
- **AND** the response body contains validation error details

#### Scenario: Service is overloaded (backpressure)
- **WHEN** a POST request is sent to `/webhooks/transaction` and the internal event queue is full
- **THEN** the response status code is 503 Service Unavailable
- **AND** the response body contains `{"status": "overloaded"}`
