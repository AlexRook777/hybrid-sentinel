# Roadmap — Hybrid Sentinel

High-level implementation plan. Each phase maps to one or more OpenSpec changes.
Update status as changes move through the lifecycle.

## Phases

| Phase | Change ID | Capability | Status |
|-------|-----------|------------|--------|
| 0 | `add-project-scaffold` | project-structure, api-ingestion | Archived |
| 1 | `add-stream-processing` | stream-processing | Not Started |
| 2 | `add-anomaly-detection` | anomaly-detection | Not Started |
| 3 | `add-agent-investigation` | agent-investigation | Not Started |

## Phase Descriptions

### Phase 0 — Project Scaffold (Complete)

Foundation: Python package, FastAPI entry point, `/health` endpoint, config, Docker, dev tooling.

### Phase 1 — Stream Processing

Deploy Bytewax stateful stream to collect data and match callbacks.

- Transaction & callback data models (Pydantic)
- Bytewax dataflow with stateful 5-minute windows
- Callback state matching (transaction-callback pairing)
- TIMEOUT anomaly emission after 300s with no callback
- Webhook ingestion endpoint (`POST /webhooks/transaction`)

**Depends on**: Phase 0

### Phase 2 — Anomaly Detection

Implement River for statistical anomaly detection and tune thresholds.

- River online ML model (incremental learning)
- Feature extraction from stream events
- Anomaly scoring (0.0-1.0 range)
- 0.85 threshold triggering investigation
- Concept drift detection (ADWIN)

**Depends on**: Phase 1 (stream output feeds anomaly scorer)

### Phase 3 — Agent Investigation

Integrate LangGraph for Slack alerts and autonomous investigation.

- LangGraph multi-step investigation agent
- Merchant failure rate analysis
- Provider pattern matching
- LLM-generated case reports
- Slack alert integration

**Depends on**: Phase 2 (anomaly alerts trigger agent)
