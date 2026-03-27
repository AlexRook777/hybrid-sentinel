## 1. Data Models

- [x] 1.1 Create `src/hybrid_sentinel/models.py` with `TransactionEvent`, `CallbackEvent`, and `AnomalyEvent` Pydantic models using a `type` discriminator field
- [x] 1.2 Add `MatchedPair` model for successfully paired transaction-callback events
- [x] 1.3 Write unit tests for model validation (valid events, missing fields, invalid status values)

## 2. Event Bus

- [x] 2.1 Create in-process event bus using `asyncio.Queue` with configurable max size
- [x] 2.2 Add `SENTINEL_QUEUE_MAX_SIZE` to `config.py` (default: 10000)
- [x] 2.3 Write tests for enqueue success and backpressure (queue full) behavior

## 3. Webhook Endpoint

- [x] 3.1 Create `src/hybrid_sentinel/routes/webhooks.py` with `POST /webhooks/transaction` endpoint accepting discriminated union payloads
- [x] 3.2 Register the webhook router in `main.py`
- [x] 3.3 Return 202 Accepted for valid events, 422 for validation errors, 503 when queue is full
- [x] 3.4 Write endpoint tests (valid transaction, valid callback, invalid payload, backpressure 503)

## 4. Bytewax Stream Processor

- [x] 4.1 Create `src/hybrid_sentinel/stream/source.py` — `DynamicSource` that reads from the asyncio Queue
- [x] 4.2 Create `src/hybrid_sentinel/stream/processor.py` — `stateful_map` callback matching logic with state class holding pending transactions
- [x] 4.3 Implement timeout detection in the processor: emit `AnomalyEvent(anomaly_type="TIMEOUT")` for entries older than `callback_timeout` seconds
- [x] 4.4 Create `src/hybrid_sentinel/stream/sink.py` — output sink that collects matched pairs and anomaly events
- [x] 4.5 Create `src/hybrid_sentinel/stream/dataflow.py` — wire source → key_on → stateful_map → sink into a Bytewax `Dataflow`
- [x] 4.6 Add `SENTINEL_CALLBACK_TIMEOUT` (default: 300) and `SENTINEL_TICK_INTERVAL` (default: 30) to `config.py`

## 5. Dataflow Lifecycle

- [x] 5.1 Start the Bytewax dataflow in a background daemon thread during FastAPI lifespan startup
- [x] 5.2 Signal the dataflow to stop during lifespan shutdown (poison pill + thread join)
- [x] 5.3 Write integration test: submit transaction → submit callback → verify matched pair is emitted
- [x] 5.4 Write integration test: submit transaction → wait for timeout → verify TIMEOUT anomaly event is emitted

## 6. Dependencies & Tooling

- [x] 6.1 Move `bytewax` from optional `[ml]` extra to core dependencies in `pyproject.toml`
- [x] 6.2 Run `uv lock` to update the lockfile
- [x] 6.3 Verify `ruff check src/` and `mypy src/` pass with new code
- [x] 6.4 Verify all tests pass with `pytest`
