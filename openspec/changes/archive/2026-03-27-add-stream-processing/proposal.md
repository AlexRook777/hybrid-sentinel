## Why

The payment gateway currently has no mechanism to track transaction-callback pairs or detect when callbacks fail to arrive. Provider degradations can go unnoticed for 15-30 minutes, causing revenue loss. The system needs a stateful stream processing layer that matches transactions to their callbacks within 5-minute windows and emits anomaly events when callbacks are missing — this is the foundational data pipeline that all downstream detection and investigation depends on.

## What Changes

- Add Pydantic data models for transaction events, callback events, and anomaly events
- Add a webhook ingestion endpoint (`POST /webhooks/transaction`) to accept transaction and callback payloads
- Implement a Bytewax stateful dataflow that:
  - Keys events by merchant + transaction ID
  - Maintains a 5-minute window of transaction state
  - Joins callbacks to their originating transactions
  - Emits a TIMEOUT anomaly event when no callback arrives within 300 seconds
- Add an in-process event bus to connect the FastAPI ingestion layer to the Bytewax dataflow
- Add configuration settings for callback timeout and window parameters

## Capabilities

### New Capabilities
- `stream-processing`: Bytewax stateful windowing, callback matching, and TIMEOUT anomaly emission

### Modified Capabilities
- `api-ingestion`: Add webhook endpoint for receiving transaction and callback events

## Impact

- **Code**: New modules in `src/hybrid_sentinel/` — models, stream dataflow, event bus, webhook route
- **API**: New `POST /webhooks/transaction` endpoint (public surface area increase)
- **Dependencies**: `bytewax` moves from optional `[ml]` extra to core dependency
- **Tests**: New test suite for stream processing logic, webhook endpoint, and timeout detection
