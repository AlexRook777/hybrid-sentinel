## MODIFIED Requirements

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
