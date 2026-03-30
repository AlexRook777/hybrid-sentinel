# Stream Processing — Phase 1 Documentation

## Table of Contents
- [Business Overview](#business-overview)
- [Technical Architecture](#technical-architecture)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Configuration](#configuration)

---

## Business Overview

### The Business Problem

Your payment gateway handles transactions like this:

```
User clicks "Pay $100"
    ↓
Gateway sends request to Payment Provider (Stripe, PayPal, etc.)
    ↓
Provider processes...
    ↓
Provider sends callback: "Success" or "Failure"
```

**The Challenge**: The callback can arrive **immediately** or **up to 5 minutes later**. During that window, you need to:
1. Remember which transaction you're waiting for
2. Match the callback when it arrives
3. Detect if the callback **never arrives** (timeout)

This is **stream processing** — handling continuous flows of events that need to be paired and monitored over time.

### Stream Processing vs Traditional Request-Response

#### Traditional API (Simple)
```
Request  ──→  [Process]  ──→  Response
   (instant, synchronous)
```

#### Stream Processing (Your Case)
```
Transaction Event ──→  [Store in Memory]
                              ↓
                         [Wait 0-300s]
                              ↓
Callback Event ──────→  [Match & Pair]  ──→  Output: Matched Pair
                              │
                              ↓ (if no callback arrives)
                       [After 300s: TIMEOUT]  ──→  Output: Anomaly Event
```

---

### What Hybrid Sentinel's Stream Processor Does

#### Business Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAYMENT GATEWAY WEBHOOK                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │    POST /webhooks/transaction           │
        │  (receives Transaction OR Callback)     │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         EVENT BUS (Queue)               │
        │   "Like a waiting room for events"      │
        └─────────────────────────────────────────┘
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════╗
║              BYTEWAX STREAM PROCESSOR                          ║
║                                                                 ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │  STATE: Pending Transactions                            │  ║
║  │  ┌───────────────────────────────────────────────────┐  │  ║
║  │  │ M1:T100 → {amount: $100, time: 14:30:00}         │  │  ║
║  │  │ M2:T200 → {amount: $50,  time: 14:29:15}         │  │  ║
║  │  │ M1:T300 → {amount: $200, time: 14:25:10} ← OLD!  │  │  ║
║  │  └───────────────────────────────────────────────────┘  │  ║
║  └─────────────────────────────────────────────────────────┘  ║
║                                                                 ║
║  Every 30 seconds: Check for transactions older than 300s      ║
╚═══════════════════════════════════════════════════════════════╝
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
         MATCHED PAIR               TIMEOUT ANOMALY
    ┌──────────────────┐      ┌──────────────────────┐
    │ Transaction: T100│      │ Transaction: T300    │
    │ Callback: Success│      │ No callback received │
    │ Time: 2.3s       │      │ Elapsed: 310s        │
    └──────────────────┘      └──────────────────────┘
                 │                         │
                 └────────────┬────────────┘
                              ▼
                    [Phase 2: River ML]
                   Anomaly Scoring (Future)
```

---

### Key Business Concepts

#### 1. Stateful Processing
Unlike a regular API that forgets about a request after responding, stream processing **remembers** transactions for up to 5 minutes.

**Analogy**: Like a restaurant host holding a table reservation:
- Guest arrives (transaction) → Name added to list
- Party shows up (callback) → Match them to reservation, seat them
- Party never shows up → After 15 minutes, release the table (timeout)

#### 2. Event Pairing
Each transaction has a unique ID. When a callback arrives with the same ID, they're "paired" like matching socks.

```
Transaction: merchant=M1, txn=T100, amount=$50
                    +
Callback:    merchant=M1, txn=T100, status=Success
                    =
Matched Pair: "M1 successfully paid $50 via T100"
```

#### 3. Timeout Detection
If no callback arrives within 300 seconds (5 minutes), emit an **anomaly event**.

**Why this matters**:
- Provider might be down
- Network issue
- Fraud attempt (someone submitted a transaction but blocked the callback)
- Provider forgot to send the callback

---

### Real-World Scenarios

#### Scenario A: Happy Path (Normal Payment)
```
14:30:00  Transaction arrives: "M1 wants to pay $100 via T100"
          → Stored in state

14:30:02  Callback arrives: "T100 succeeded"
          → Matched! Remove from state
          → Output: MatchedPair(transaction, callback)

Time elapsed: 2 seconds ✓
```

#### Scenario B: Slow Provider (5 minutes)
```
14:30:00  Transaction arrives: "M2 wants to pay $50 via T200"
          → Stored in state

14:35:00  Callback arrives: "T200 succeeded" (exactly 5 min)
          → Matched! Remove from state
          → Output: MatchedPair(transaction, callback)

Time elapsed: 300 seconds ✓ (barely made it!)
```

#### Scenario C: Provider Timeout (Anomaly)
```
14:30:00  Transaction arrives: "M3 wants to pay $200 via T300"
          → Stored in state

14:30:30  [Tick check] Only 30s elapsed, keep waiting...
14:31:00  [Tick check] Only 60s elapsed, keep waiting...
...
14:35:00  [Tick check] Only 300s elapsed, keep waiting...
14:35:30  [Tick check] 330s elapsed → TIMEOUT!
          → Remove from state
          → Output: AnomalyEvent(type=TIMEOUT, txn=T300)

Time elapsed: 330 seconds ✗ (callback never arrived)
```

---

### Why "Stream" Processing?

Because events arrive as a **continuous stream**, not one-off requests:

```
Time ─────────────────────────────────────────────────────▶

Events:  T  C  T  T  C  T  C  T  T  C  T  C  C  T ...

T = Transaction
C = Callback

The processor handles ALL of them in real-time,
pairing them up as callbacks arrive.
```

---

### Business Value

| Traditional Approach | Stream Processing (Bytewax) |
|---------------------|----------------------------|
| Poll database every 10s for pending transactions | Events processed instantly |
| Database query per check (expensive) | In-memory state (fast) |
| Hard to detect patterns across many transactions | Natural aggregation and pattern detection |
| Difficult to scale to 10k TPS | Designed for high throughput |

**Bottom line**: Stream processing lets you handle **180K transactions/day** (current load) with room to scale to **86M transactions/day** without changing the architecture.

---

## Technical Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI | HTTP webhook endpoints |
| **Stream Engine** | Bytewax 0.21+ | Stateful stream processing (Rust-based) |
| **Event Bus** | `queue.Queue` | Thread-safe in-process queue |
| **Data Validation** | Pydantic | Event model validation |
| **Concurrency** | Threading | Background dataflow + tick generator |

### System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Process                           │
│                                                                    │
│  ┌────────────────┐      ┌─────────────────┐                     │
│  │  Webhook       │      │  Event Bus      │                     │
│  │  Endpoint      │─────▶│  (queue.Queue)  │                     │
│  │  (async)       │      │  Max: 10,000    │                     │
│  └────────────────┘      └─────────────────┘                     │
│                                   │                                │
│                                   │ .dequeue()                     │
│                                   ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          Bytewax Dataflow (Background Thread)               │ │
│  │                                                               │ │
│  │  EventQueueSource → key_on → stateful_map → flat_map → Sink│ │
│  │                         │                                    │ │
│  │                         └─ CallbackMatcherState              │ │
│  │                            (per-key state)                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                   ▲                                │
│                                   │ TickEvent(key)                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │     Tick Generator (Background Thread)                      │ │
│  │     - Every 30s: inject TickEvent for each active key       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Module Breakdown

```
src/hybrid_sentinel/
├── routes/
│   └── webhooks.py          # POST /webhooks/transaction endpoint
├── event_bus.py             # Thread-safe queue (queue.Queue)
├── models.py                # Pydantic models (Transaction, Callback, Anomaly, MatchedPair)
└── stream/
    ├── source.py            # EventQueueSource (reads from event_bus)
    ├── processor.py         # CallbackMatcherState + callback_matcher function
    ├── sink.py              # EventCollectorSink (outputs to in-memory lists)
    └── dataflow.py          # Bytewax dataflow wiring + tick_generator
```

---

### Bytewax Dataflow Pipeline

#### Operators Flow

```python
flow = Dataflow("hybrid-sentinel-stream")

# 1. INPUT: Read from event bus queue
input_stream = op.input("event_source", flow, EventQueueSource())

# 2. KEY_ON: Partition by merchant_id:transaction_id
keyed_stream = op.key_on("key_events", input_stream, get_event_key)

# 3. STATEFUL_MAP: Callback matching logic (per-key state)
matched_stream = op.stateful_map("callback_matcher", keyed_stream, callback_matcher)

# 4. FLAT_MAP: Flatten list outputs from stateful_map
flattened_stream = op.flat_map("flatten", matched_stream, lambda kv: kv[1])

# 5. OUTPUT: Collect matched pairs and anomaly events
op.output("event_collector", flattened_stream, EventCollectorSink())
```

#### State Management

Each unique key (e.g., `"M1:T100"`) gets its own `CallbackMatcherState`:

```python
class CallbackMatcherState:
    pending_transactions: dict[str, TransactionState]

    def process_event(event: TransactionEvent | CallbackEvent):
        # Store transaction OR match callback

    def check_timeouts():
        # Emit TIMEOUT anomalies for old transactions
```

**Active Keys Registry**: A thread-safe global set tracks which keys have pending transactions. The tick generator reads this to know which keys need timeout checks.

#### Timeout Detection Mechanism

```
Every 30 seconds:
    for each key in active_keys:
        event_bus.enqueue(TickEvent(key=key))

Bytewax routes TickEvent(key="M1:T100") to the state for key "M1:T100"
    → CallbackMatcherState.check_timeouts() is called
    → If transaction is >300s old: emit AnomalyEvent
```

---

### Event Bus (queue.Queue)

**Location**: `src/hybrid_sentinel/event_bus.py`

**Design**: Thread-safe `queue.Queue` (stdlib) with:
- **Max size**: 10,000 events (configurable via `SENTINEL_QUEUE_MAX_SIZE`)
- **Backpressure**: Returns `False` from `enqueue()` when full (triggers 503 response)
- **Blocking dequeue**: Source polls with 0.5s timeout

**Key Methods**:
```python
def enqueue(event) -> bool:  # Sync, non-blocking
def dequeue(timeout=1.0) -> object | None:  # Sync, blocking with timeout
def stop():  # Signal shutdown
def reset():  # Clear for tests
```

**Thread Safety**: `queue.Queue` is thread-safe by design (GIL-protected). Webhook endpoint (async FastAPI) and Bytewax thread (sync) both safely access it.

---

## API Reference

### POST /webhooks/transaction

**Endpoint**: `POST /webhooks/transaction`
**Purpose**: Ingest transaction or callback events from payment gateway
**Content-Type**: `application/json`

#### Request Body (Discriminated Union)

**Transaction Event**:
```json
{
  "type": "transaction",
  "merchant_id": "M123",
  "transaction_id": "T456",
  "amount": "100.50",
  "currency": "USD",
  "provider_id": "stripe",
  "timestamp": "2026-03-27T14:30:00Z"
}
```

**Callback Event**:
```json
{
  "type": "callback",
  "merchant_id": "M123",
  "transaction_id": "T456",
  "status": "success",
  "actual_amount": "100.50",
  "actual_currency": "USD",
  "provider_id": "stripe",
  "timestamp": "2026-03-27T14:30:02Z"
}
```

#### Response Codes

| Code | Meaning | Response Body |
|------|---------|---------------|
| **202 Accepted** | Event enqueued successfully | `{"status": "accepted"}` |
| **422 Unprocessable Entity** | Validation error (invalid JSON, missing fields, wrong types) | `{"detail": [...]}` |
| **503 Service Unavailable** | Event queue is full (backpressure) | `{"detail": {"status": "overloaded"}}` |

#### Field Validation

**Transaction**:
- `merchant_id`: Non-empty string (min_length=1)
- `transaction_id`: Non-empty string (min_length=1)
- `amount`: Decimal > 0
- `currency`: Exactly 3 characters (e.g., "USD", "EUR")
- `provider_id`: Non-empty string
- `timestamp`: ISO 8601 datetime
- `type`: Must be `"transaction"`

**Callback**:
- `merchant_id`: Non-empty string
- `transaction_id`: Non-empty string
- `status`: One of `"success"`, `"failure"`, `"pending"`
- `actual_amount`: Decimal > 0 (the actual amount charged)
- `actual_currency`: Exactly 3 characters (e.g., "USD", "EUR")
- `provider_id`: Non-empty string
- `timestamp`: ISO 8601 datetime
- `type`: Must be `"callback"`

#### Examples

**Valid Transaction**:
```bash
curl -X POST http://localhost:8000/webhooks/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "transaction",
    "merchant_id": "M1",
    "transaction_id": "T100",
    "amount": "99.99",
    "currency": "USD",
    "provider_id": "paypal",
    "timestamp": "2026-03-27T10:00:00Z"
  }'
```

**Response**:
```json
{
  "status": "accepted"
}
```

**Invalid (Missing Fields)**:
```bash
curl -X POST http://localhost:8000/webhooks/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "transaction",
    "merchant_id": "M1"
  }'
```

**Response** (422):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "transaction_id"],
      "msg": "Field required"
    },
    ...
  ]
}
```

---

## Data Models

All models defined in `src/hybrid_sentinel/models.py` using Pydantic.

### TransactionEvent

```python
class TransactionEvent(BaseModel):
    type: Literal["transaction"] = "transaction"
    merchant_id: str = Field(..., min_length=1)
    transaction_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    provider_id: str = Field(..., min_length=1)
    timestamp: datetime
```

### CallbackEvent

```python
class CallbackEvent(BaseModel):
    type: Literal["callback"] = "callback"
    merchant_id: str = Field(..., min_length=1)
    transaction_id: str = Field(..., min_length=1)
    status: Literal["success", "failure", "pending"]
    actual_amount: Decimal = Field(..., gt=0)
    actual_currency: str = Field(..., min_length=3, max_length=3)
    provider_id: str = Field(..., min_length=1)
    timestamp: datetime
```

**Fields**:
- `actual_amount`: The actual amount charged by the payment provider (required, must be > 0)
- `actual_currency`: The actual currency used for the charge (required, exactly 3 characters, e.g., "USD", "EUR")

**Reconciliation Note**: Payment providers allow payers to modify amounts/currencies within their payment widgets. The `actual_amount` and `actual_currency` fields capture what was actually charged, which may differ from the originally requested `transaction.amount` and `transaction.currency`. This enables:
- Revenue reconciliation (detecting when paid amount ≠ requested amount)
- Fraud detection (flagging unexpected amount changes)
- Dispute resolution (maintaining audit trail of actual vs. requested amounts)

### AnomalyEvent

```python
class AnomalyEvent(BaseModel):
    type: Literal["anomaly"] = "anomaly"
    anomaly_type: str  # e.g., "TIMEOUT"
    merchant_id: str
    transaction_id: str
    provider_id: str
    timestamp: datetime
    details: dict = Field(default_factory=dict)
```

**Example TIMEOUT Anomaly**:
```python
AnomalyEvent(
    anomaly_type="TIMEOUT",
    merchant_id="M1",
    transaction_id="T100",
    provider_id="stripe",
    timestamp=datetime.now(UTC),
    details={"elapsed_seconds": 310}
)
```

### MatchedPair

```python
class MatchedPair(BaseModel):
    transaction: TransactionEvent
    callback: CallbackEvent
    match_timestamp: datetime
```

### IncomingEvent (Union Type)

```python
IncomingEvent = TransactionEvent | CallbackEvent
```

Used for the webhook endpoint discriminated union.

---

## Configuration

All settings via environment variables with `SENTINEL_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTINEL_APP_NAME` | `"hybrid-sentinel"` | Application name |
| `SENTINEL_LOG_LEVEL` | `"INFO"` | Logging level |
| `SENTINEL_HOST` | `"0.0.0.0"` | Bind host |
| `SENTINEL_PORT` | `8000` | Bind port |
| `SENTINEL_QUEUE_MAX_SIZE` | `10000` | Max event bus queue size |
| `SENTINEL_CALLBACK_TIMEOUT` | `300` | Timeout threshold (seconds) |
| `SENTINEL_TICK_INTERVAL` | `30` | Tick interval (seconds) |

**Example** (`.env` file):
```bash
SENTINEL_LOG_LEVEL=DEBUG
SENTINEL_CALLBACK_TIMEOUT=120
SENTINEL_TICK_INTERVAL=10
```

**Loading**:
```python
from hybrid_sentinel.config import settings

print(settings.callback_timeout)  # 120
```

---

## Performance Characteristics

### Throughput

**Current Load**: 180K transactions/day (~2 TPS)
**Single-Process Ceiling**: ~86M transactions/day (~1,000 TPS)

**Bottlenecks**:
- Event bus queue (10K events = ~5 seconds buffer at 2K TPS)
- In-memory state (grows with pending transactions)
- Timeout sweep (O(n) per key per tick)

**Scaling Path**:
- Phase 2: Replace in-memory sink with River scoring pipeline
- Production: Use Bytewax `cluster_main` for multi-worker deployment
- Future: Replace `queue.Queue` with Redpanda/Kafka for distributed queue

### Memory Usage

**Per Pending Transaction**: ~500 bytes
**10K Pending**: ~5 MB
**100K Pending**: ~50 MB

**Sink Lists** (unbounded in Phase 1):
- `matched_pairs`: grows until app restart
- `anomaly_events`: grows until app restart

**Mitigation**: Phase 2 replaces sink with streaming output.

---

## Testing

**Test Coverage**: 36 tests (100% pass)

### Unit Tests
- `test_models.py` — Pydantic validation
- `test_event_bus.py` — Queue operations, backpressure
- `test_webhooks.py` — Endpoint responses (202/422/503)
- `test_processor.py` — Callback matching, timeout detection

### Integration Tests
- `test_integration.py` (marked with `@pytest.mark.integration`)
  - Transaction-callback matching (end-to-end)
  - Timeout anomaly detection (end-to-end)

**Run Tests**:
```bash
# Unit tests only
pytest tests/ -m "not integration"

# All tests (including integration)
pytest tests/

# Integration tests only
pytest tests/ -m integration
```

---

## Deployment

### Docker

**Build**:
```bash
docker build -t hybrid-sentinel:latest .
```

**Run**:
```bash
docker run -p 8000:8000 \
  -e SENTINEL_LOG_LEVEL=DEBUG \
  -e SENTINEL_CALLBACK_TIMEOUT=300 \
  hybrid-sentinel:latest
```

**Security**: Container runs as non-root user `appuser` (fixes OWASP A04).

### Local Development

```bash
# Install dependencies
uv sync

# Run server
uv run uvicorn hybrid_sentinel.main:app --reload

# Run tests
uv run pytest tests/
```

---

## What's Next (Phase 2)

✅ Phase 1 Complete: Stream processing with callback matching and timeout detection

**Phase 2 Goals** (River Anomaly Detection):
1. Replace in-memory sink with River scoring pipeline
2. Extract features from MatchedPair and AnomalyEvent
3. Train incremental ML model (anomaly score 0.0-1.0)
4. Emit high-score anomalies (>0.85) to Phase 3

See `openspec/ROADMAP.md` for full project plan.
