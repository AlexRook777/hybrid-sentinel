## 1. Dependencies & Configuration

- [x] 1.1 Add `langgraph`, `langchain`, and `langchain-core` to pyproject.toml dependencies
- [x] 1.2 Add investigation agent settings to `config.py`: `agent_enabled`, `agent_llm_model`, `agent_lookback_minutes`, `investigation_queue_max_size`
- [x] 1.3 Add `CaseReport` model to `models.py` with all fields from design D5

## 2. Agent Module Structure

- [x] 2.1 Create `src/hybrid_sentinel/agent/__init__.py` with `investigation_bus`, `start_agent()`, `stop_agent()`, `get_agent()` exports
- [x] 2.2 Create `src/hybrid_sentinel/agent/state.py` with `InvestigationState` TypedDict (design D8)

## 3. Context Computation

- [x] 3.1 Create `src/hybrid_sentinel/agent/context.py` with `compute_merchant_stats()` — failure rate, avg latency, event count from matched_pairs
- [x] 3.2 Add `compute_provider_stats()` to context.py — failure rate, affected merchants, total merchants within lookback window
- [x] 3.3 Write tests for merchant stats computation (zero data, normal data, failure rate accuracy)
- [x] 3.4 Write tests for provider stats computation (lookback window filtering, multi-merchant counting)

## 4. Graph Nodes

- [x] 4.1 Create `src/hybrid_sentinel/agent/nodes.py` with `gather_context` node — reads from in-memory lists, populates merchant_stats and provider_stats
- [x] 4.2 Add `analyze_patterns` node — pattern classification (provider_outage, merchant_targeting, timeout_cluster, behavioral) and severity assignment per design D6
- [x] 4.3 Add `generate_report` node — LLM call via `init_chat_model` or template-based mock mode, with LLM error fallback
- [x] 4.4 Create `src/hybrid_sentinel/agent/alerts.py` with `log_alert` node — structured logging of case report
- [x] 4.5 Write tests for pattern classification rules (all 4 patterns, edge cases)
- [x] 4.6 Write tests for severity assignment (CRITICAL/HIGH/MEDIUM/LOW conditions)
- [x] 4.7 Write tests for mock report generation (template output, no LLM dependency)

## 5. LangGraph Pipeline

- [x] 5.1 Create `src/hybrid_sentinel/agent/graph.py` with `build_investigation_graph()` — linear StateGraph: gather_context → analyze_patterns → generate_report → log_alert
- [x] 5.2 Write test for full graph execution with mock data (end-to-end single investigation)

## 6. Scorer Integration

- [x] 6.1 Modify `src/hybrid_sentinel/anomaly/scorer.py` to import `investigation_bus`
- [x] 6.2 In `score_event`, after appending to `_scored_anomalies`, call `investigation_bus.enqueue(scored_event)`
- [x] 6.3 Write test for scorer → investigation bus publication (mock scoring_bus, feed one pair, check if investigation_bus gets it)
- [x] 6.4 Write test for investigation bus backpressure (fill investigation_bus to `max_size`, make sure scorer doesn't block or crash)

## 7. Agent Lifecycle

- [x] 7.1 Implement background thread in `src/hybrid_sentinel/agent/__init__.py` — dequeue from `investigation_bus`, invoke graph, store CaseReport in in-memory list (`_recent_cases`)
- [x] 7.2 Create `src/hybrid_sentinel/agent/store.py` with `get_recent_cases()`, `add_case()`, and ThreadLock
- [x] 7.3 Write test for investigation background processing
- [x] 7.4 Modify `src/hybrid_sentinel/main.py` lifespan to call `agent.start_agent()` and `agent.stop_agent()`
- [x] 7.5 Write test for agent start/stop lifecycle

## 8. API Endpoints

- [x] 8.1 Create `src/hybrid_sentinel/routes/cases.py` with `GET /cases` (list all), `GET /cases/{case_id}` (single), `GET /cases/stats` (statistics)
- [x] 8.2 Register cases router in `main.py`
- [x] 8.3 Write tests for all three case endpoints (list, get by ID, 404, stats)

## 9. Integration Tests

- [x] 9.1 Write end-to-end test: scored anomaly → investigation bus → agent → case report stored → retrievable via API
- [x] 9.2 Write test for agent disabled via config (no agent thread, investigation bus not created)
- [x] 9.3 Run full test suite and verify all existing + new tests pass
