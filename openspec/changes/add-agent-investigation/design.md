## Context

Phase 2 produces scored AnomalyEvents (score >= 0.85 or DRIFT type) that are collected in an in-memory list. There is no mechanism to investigate these anomalies or provide human-actionable context. Operations teams see raw anomaly data with no analysis of whether the issue is merchant-specific, provider-wide, or a transient blip.

The system already has in-memory lists of `matched_pairs` (all transaction-callback pairs) and `anomaly_events` (all Phase 1 TIMEOUT events). These contain the raw material needed to compute merchant/provider historical statistics without an external database.

LangGraph is already a project decision (from the blueprint). The event bus subscriber pattern from Phase 2 provides a natural integration point.

## Goals / Non-Goals

**Goals:**
- Autonomously investigate each anomaly by computing merchant and provider context
- Classify anomaly patterns (provider outage, merchant targeting, general behavioral)
- Generate LLM-powered case reports with actionable recommendations
- Log all investigations as structured case reports for review
- Expose case reports via API endpoints
- Support any LangChain-compatible LLM (pluggable via `init_chat_model`)
- Work without external infrastructure (no database, no Slack)

**Non-Goals:**
- Real Slack integration (log-only for MVP; Slack is a future phase)
- Alert throttling (no Slack means no spam concern)
- Persistent storage of case reports (in-memory, same pattern as Phase 1/2)
- External database for merchant/provider history (computed from in-memory data)
- Human-in-the-loop approval before alert (fully autonomous for MVP)
- Multi-turn agent conversations (single-pass investigation graph)

## Decisions

### D1: Investigation Bus Pattern (Decoupled from Scorer)

The anomaly scorer publishes scored AnomalyEvents to an `investigation_bus` (new EventBus instance). The investigation agent consumes from this bus in its own background thread.

**Why**: Same decoupling pattern as Phase 2 (scoring_bus). The agent can be tested, disabled, or replaced independently. The scorer never blocks waiting for investigations to complete.

**Implementation**: When `score >= threshold` or DRIFT is detected, the scorer enqueues the AnomalyEvent on the investigation bus (non-blocking, log on drop). The agent's background thread dequeues and processes.

### D2: Linear LangGraph (No Conditional Branching for MVP)

The investigation graph is a simple linear pipeline:

```
START → gather_context → analyze_patterns → generate_report → log_alert → END
```

**Why**: The blueprint describes a 3-step sequential process (query merchant → check provider → generate report). For MVP, every anomaly follows the same path. Conditional branching (e.g., skip LLM if context shows obvious false positive) can be added later without changing the graph structure.

**Nodes**:

| Node | Input | Output | Side Effects |
|------|-------|--------|-------------|
| `gather_context` | AnomalyEvent | merchant_stats, provider_stats | Reads from Phase 1/2 in-memory lists |
| `analyze_patterns` | merchant_stats, provider_stats | severity, pattern_type | None |
| `generate_report` | All accumulated state | case_report text | Calls LLM (or mock) |
| `log_alert` | case_report | slack_logged=True | Logs structured alert |

### D3: Pluggable LLM via init_chat_model

Use `langchain`'s `init_chat_model(model_name)` to instantiate any LangChain-compatible chat model. The model name is configurable via `SENTINEL_AGENT_LLM_MODEL`.

**Why**: The user wants flexibility to swap between Claude, GPT-4, local models, etc. `init_chat_model` handles provider detection from the model name string (e.g., `"claude-sonnet-4-5-20250929"` → Anthropic, `"gpt-4o"` → OpenAI).

**Mock mode**: When `SENTINEL_AGENT_LLM_MODEL` is empty or `"mock"`, the generate_report node uses a template-based report without calling any LLM. This enables testing without API keys.

### D4: In-Memory Merchant/Provider Context

Merchant historical stats and provider correlation are computed on-the-fly from Phase 1/2 in-memory lists (`matched_pairs`, `anomaly_events`, `_scored_anomalies`).

**Why**: No external database needed. The data is already available in-process. Computation is O(n) over the lists but acceptable for the expected volume (10K-100K events in memory).

**Computed metrics**:

| Metric | Source | Computation |
|--------|--------|-------------|
| merchant failure rate | `matched_pairs` filtered by merchant_id | count(failure) / count(total) |
| merchant avg latency | `matched_pairs` filtered by merchant_id | mean(callback.ts - txn.ts) |
| merchant event count | `matched_pairs` filtered by merchant_id | count |
| provider failure rate (recent) | `matched_pairs` filtered by provider_id, last N minutes | count(failure) / count(total) |
| provider affected merchants | `matched_pairs` filtered by provider_id, last N minutes, status=failure | count(distinct merchant_id) |
| provider total merchants | `matched_pairs` filtered by provider_id, last N minutes | count(distinct merchant_id) |

**Lookback window**: Configurable `SENTINEL_AGENT_LOOKBACK_MINUTES` (default 10) for provider correlation. Merchant stats use all available data.

### D5: CaseReport Model

A Pydantic model capturing the full investigation output:

```python
class CaseReport(BaseModel):
    case_id: str                  # UUID
    anomaly_event: AnomalyEvent   # The triggering anomaly
    severity: str                 # CRITICAL, HIGH, MEDIUM, LOW
    pattern: str                  # provider_outage, merchant_targeting, behavioral, timeout_cluster
    merchant_failure_rate: float  # Historical failure rate
    merchant_avg_latency: float   # Historical avg callback latency (seconds)
    merchant_event_count: int     # Total events seen for this merchant
    provider_failure_rate: float  # Recent failure rate (lookback window)
    provider_affected_merchants: int  # How many merchants affected
    recommendation: str           # LLM-generated (or template) recommendation
    investigation_duration_ms: int  # How long the investigation took
    timestamp: datetime           # When the investigation completed
```

### D6: Pattern Classification Rules

After gathering context, the agent classifies the anomaly into a pattern:

| Pattern | Condition |
|---------|-----------|
| `provider_outage` | provider_affected_merchants >= 3 AND provider_failure_rate > 10% |
| `merchant_targeting` | merchant_failure_rate > 5x historical AND provider_affected_merchants <= 1 |
| `timeout_cluster` | anomaly_type == "TIMEOUT" AND provider_failure_rate > 5% |
| `behavioral` | Catch-all for scored anomalies not matching above patterns |

**Severity mapping**:

| Severity | Condition |
|----------|-----------|
| `CRITICAL` | provider_outage with affected_merchants >= 5 |
| `HIGH` | provider_outage OR merchant_targeting |
| `MEDIUM` | timeout_cluster OR anomaly_score >= 0.95 |
| `LOW` | behavioral catch-all |

### D7: Module Structure

```
src/hybrid_sentinel/agent/
├── __init__.py          # investigation_bus, start_agent(), stop_agent(), get_agent()
├── graph.py             # build_investigation_graph() → compiled StateGraph
├── nodes.py             # gather_context(), analyze_patterns(), generate_report(), log_alert()
├── state.py             # InvestigationState TypedDict
├── context.py           # compute_merchant_stats(), compute_provider_stats()
└── alerts.py            # log_case_report() — structured logging output
```

The agent lifecycle follows the same pattern as the scorer: `start_agent()` / `stop_agent()` in the FastAPI lifespan, background thread consuming from `investigation_bus`.

### D8: LangGraph State Schema

```python
class InvestigationState(TypedDict):
    anomaly_event: dict           # AnomalyEvent serialized as dict
    merchant_stats: dict          # {failure_rate, avg_latency, event_count}
    provider_stats: dict          # {failure_rate, affected_merchants, total_merchants}
    severity: str                 # CRITICAL/HIGH/MEDIUM/LOW
    pattern: str                  # provider_outage/merchant_targeting/etc.
    recommendation: str           # LLM or template output
    case_id: str                  # UUID for the case
    investigation_start_ms: float # monotonic time for duration tracking
```

LangGraph requires dict-serializable state. AnomalyEvent is serialized via `.model_dump()`.

## Risks / Trade-offs

**[In-memory data loss on restart]** → All merchant/provider context is lost when the process restarts. The agent starts with zero historical context and builds it up as events flow in. Mitigation: Phase 2 warmup ensures the scorer doesn't emit anomalies until 1000 events are processed, giving the context module sufficient data.

**[O(n) context computation]** → Computing merchant stats requires iterating all `matched_pairs`. For 100K pairs, this is ~10ms. For 1M pairs, ~100ms. Mitigation: Acceptable for MVP throughput. If it becomes a bottleneck, precompute rolling stats on each pair arrival.

**[LLM latency and cost]** → Each investigation calls an LLM. At 5 anomalies/hour and $0.01/call, cost is negligible. At 100 anomalies/hour, latency queuing becomes an issue. Mitigation: Mock mode for testing. Log-only means no user-facing latency concern. Investigation bus provides backpressure.

**[LLM API key required for non-mock mode]** → If `SENTINEL_AGENT_LLM_MODEL` is set to a real model but the API key env var is missing, the agent will fail on first investigation. Mitigation: Agent catches LLM errors and falls back to template-based reports with a warning.

**[Thread safety for context reads]** → The agent thread reads `matched_pairs` and `anomaly_events` while the Bytewax sink thread writes to them. Both lists are protected by `_sink_lock` for appends, but iteration during reads is not locked. Mitigation: Copy the list reference before iterating (Python list iteration on a snapshot is thread-safe for append-only lists due to the GIL).
