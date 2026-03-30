## 1. Dependencies & Configuration

- [ ] 1.1 Add `langgraph`, `langchain`, and `langchain-core` to pyproject.toml dependencies
- [ ] 1.2 Add investigation agent settings to `config.py`: `agent_enabled`, `agent_llm_model`, `agent_lookback_minutes`, `investigation_queue_max_size`
- [ ] 1.3 Add `CaseReport` model to `models.py` with all fields from design D5

## 2. Agent Module Structure

- [ ] 2.1 Create `src/hybrid_sentinel/agent/__init__.py` with `investigation_bus`, `start_agent()`, `stop_agent()`, `get_agent()` exports
- [ ] 2.2 Create `src/hybrid_sentinel/agent/state.py` with `InvestigationState` TypedDict (design D8)

## 3. Context Computation

- [ ] 3.1 Create `src/hybrid_sentinel/agent/context.py` with `compute_merchant_stats()` — failure rate, avg latency, event count from matched_pairs
- [ ] 3.2 Add `compute_provider_stats()` to context.py — failure rate, affected merchants, total merchants within lookback window
- [ ] 3.3 Write tests for merchant stats computation (zero data, normal data, failure rate accuracy)
- [ ] 3.4 Write tests for provider stats computation (lookback window filtering, multi-merchant counting)

## 4. Graph Nodes

- [ ] 4.1 Create `src/hybrid_sentinel/agent/nodes.py` with `gather_context` node — reads from in-memory lists, populates merchant_stats and provider_stats
- [ ] 4.2 Add `analyze_patterns` node — pattern classification (provider_outage, merchant_targeting, timeout_cluster, behavioral) and severity assignment per design D6
- [ ] 4.3 Add `generate_report` node — LLM call via `init_chat_model` or template-based mock mode, with LLM error fallback
- [ ] 4.4 Create `src/hybrid_sentinel/agent/alerts.py` with `log_alert` node — structured logging of case report
- [ ] 4.5 Write tests for pattern classification rules (all 4 patterns, edge cases)
- [ ] 4.6 Write tests for severity assignment (CRITICAL/HIGH/MEDIUM/LOW conditions)
- [ ] 4.7 Write tests for mock report generation (template output, no LLM dependency)

## 5. LangGraph Pipeline

- [ ] 5.1 Create `src/hybrid_sentinel/agent/graph.py` with `build_investigation_graph()` — linear StateGraph: gather_context → analyze_patterns → generate_report → log_alert
- [ ] 5.2 Write test for full graph execution with mock data (end-to-end single investigation)

## 6. Scorer Integration

- [ ] 6.1 Modify `anomaly/scorer.py` to publish scored AnomalyEvents (score >= threshold or DRIFT) to investigation bus (non-blocking, log on drop)
- [ ] 6.2 Write test for scorer → investigation bus publication (scored event forwarded, below-threshold not forwarded)
- [ ] 6.3 Write test for investigation bus backpressure (full bus logs warning, scorer not blocked)

## 7. Agent Lifecycle

- [ ] 7.1 Implement background thread in `agent/__init__.py` — dequeue from investigation bus, invoke graph, store CaseReport
- [ ] 7.2 Add `start_agent()` / `stop_agent()` to FastAPI lifespan in `main.py`
- [ ] 7.3 Write test for agent lifecycle (start/stop, graceful shutdown)

## 8. API Endpoints

- [ ] 8.1 Create `src/hybrid_sentinel/routes/cases.py` with `GET /cases` (list all), `GET /cases/{case_id}` (single), `GET /cases/stats` (statistics)
- [ ] 8.2 Register cases router in `main.py`
- [ ] 8.3 Write tests for all three case endpoints (list, get by ID, 404, stats)

## 9. Integration Tests

- [ ] 9.1 Write end-to-end test: scored anomaly → investigation bus → agent → case report stored → retrievable via API
- [ ] 9.2 Write test for agent disabled via config (no agent thread, investigation bus not created)
- [ ] 9.3 Run full test suite and verify all existing + new tests pass
