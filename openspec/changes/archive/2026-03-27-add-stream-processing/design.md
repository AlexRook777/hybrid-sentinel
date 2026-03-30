## Context

Hybrid Sentinel has a running FastAPI scaffold with a `/health` endpoint and Pydantic-based configuration. There is no transaction processing logic yet. The blueprint calls for Bytewax stateful stream processing as the foundational data pipeline (Phase 1) that feeds anomaly detection (Phase 2) and agent investigation (Phase 3).

The payment gateway sends transaction initiation events and, up to 5 minutes later, callback events confirming success or failure. The stream processor must pair these events and detect missing callbacks.

## Goals / Non-Goals

**Goals:**
- Accept transaction and callback events via HTTP webhook
- Pair callbacks to their originating transactions using stateful processing
- Emit TIMEOUT anomaly events when callbacks don't arrive within 300 seconds
- Keep the design simple enough to run in a single process (no Redpanda/Kafka required yet)
- Produce a clean event stream that Phase 2 (River anomaly detection) can consume

**Non-Goals:**
- Multi-node / distributed Bytewax deployment (single-process is sufficient for Phase 1)
- Anomaly scoring — that's Phase 2 (River)
- Agent investigation — that's Phase 3 (LangGraph)
- Redpanda/Kafka integration — direct webhook ingestion is sufficient at current scale
- Persistent state recovery (Bytewax supports it, but not needed until production hardening)

## Decisions

### 1. In-process event bus via `asyncio.Queue`

**Decision**: Use a simple `asyncio.Queue` to connect FastAPI webhook handlers to the Bytewax dataflow input.

**Alternatives considered**:
- **Redpanda/Kafka**: Adds infrastructure complexity with no benefit at Phase 1 scale. Can be added later as an input source swap.
- **Python `multiprocessing.Queue`**: Bytewax runs its own thread; asyncio Queue is simpler and sufficient for single-process deployment.

**Rationale**: Keeps the system zero-dependency-on-infra for local dev and testing. The Bytewax `DynamicSource` will poll the queue.

### 2. Event keying: `merchant_id:transaction_id`

**Decision**: Key all events by `{merchant_id}:{transaction_id}` composite key.

**Rationale**: This ensures transaction-callback pairs land in the same Bytewax state partition. Merchant ID is included to prevent cross-merchant collision on transaction IDs.

### 3. Bytewax `stateful_map` for callback matching (not windowing operator)

**Decision**: Use `op.stateful_map` with a custom state class instead of Bytewax's built-in windowing operators.

**Alternatives considered**:
- **`TumblingWindower` / `SessionWindower`**: Bytewax windowing operators are designed for aggregation (sum, count). Our use case is event pairing with a timeout — a state machine, not an aggregation.

**Rationale**: `stateful_map` gives full control over the state lifecycle. The state holds the transaction timestamp and status. When a callback arrives, it joins. A periodic check emits TIMEOUT for stale entries.

### 4. Timeout detection via periodic sweep

**Decision**: Run a background task that periodically injects a "tick" event into the dataflow. The `stateful_map` handler checks for expired entries on each tick.

**Alternatives considered**:
- **Bytewax clock-based windows**: Would require artificially mapping our pairing problem into a windowing paradigm.
- **External scheduler (APScheduler)**: Adds a dependency; the tick injection is simpler.

**Rationale**: Bytewax processes events sequentially per key. A tick event with a special sentinel key broadcasts to all state partitions, triggering expiry checks. Tick interval of 30 seconds balances latency vs overhead.

### 5. Data models as Pydantic models with discriminated union

**Decision**: Define `TransactionEvent`, `CallbackEvent`, and `AnomalyEvent` as Pydantic models. Use a `type` discriminator field for the webhook endpoint to accept both transaction and callback payloads.

**Rationale**: Pydantic gives us validation at the API boundary. Discriminated unions let a single endpoint handle both event types cleanly.

### 6. Bytewax dataflow runs in a background thread

**Decision**: Start the Bytewax dataflow in a daemon thread during FastAPI's lifespan startup.

**Rationale**: Bytewax's `run_main()` is blocking. Running it in a daemon thread lets it coexist with the async FastAPI event loop. The `asyncio.Queue` bridges the two.

### 7. Output sink emits to an in-process callback list

**Decision**: Bytewax output sink appends matched pairs and anomaly events to an in-process list/queue that Phase 2 will consume.

**Rationale**: Keeps Phase 1 self-contained. Phase 2 will replace this with its River scoring pipeline.

## Module Structure

```
src/hybrid_sentinel/
├── __init__.py
├── config.py              # Extended with stream processing settings
├── main.py                # Extended with webhook route + dataflow startup
├── models.py              # NEW — Pydantic event models
├── stream/
│   ├── __init__.py
│   ├── source.py          # NEW — DynamicSource reading from asyncio.Queue
│   ├── processor.py       # NEW — stateful_map logic (pairing + timeout)
│   ├── sink.py            # NEW — Output sink for matched/anomaly events
│   └── dataflow.py        # NEW — Bytewax Dataflow wiring
└── routes/
    ├── __init__.py
    └── webhooks.py         # NEW — POST /webhooks/transaction endpoint
```

## Risks / Trade-offs

- **[In-memory state is volatile]** → Acceptable for Phase 1. Bytewax supports recovery snapshots; we'll add persistence in a hardening change.
- **[Single-process throughput ceiling]** → Bytewax can scale to multiple workers later. At 1k-10k TPS the single-process Rust engine is sufficient.
- **[Tick-based timeout has up to 30s jitter]** → A transaction timing out at 300s may be detected between 300-330s. Acceptable for the 5-minute callback window.
- **[asyncio.Queue backpressure]** → If Bytewax falls behind, the queue grows in memory. Mitigation: set a max queue size and return 503 from the webhook when full.
