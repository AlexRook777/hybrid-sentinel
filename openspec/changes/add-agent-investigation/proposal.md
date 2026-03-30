## Why

Phase 2 detects anomalies and emits scored events, but there is no intelligence to investigate them. Every alert with score >= 0.85 looks the same — whether it's a transient provider hiccup, a BIN attack targeting a specific merchant, or a full provider outage affecting dozens of merchants. Operations teams must manually query historical data, cross-reference providers, and write incident summaries. Phase 3 adds a LangGraph-based AI agent that autonomously investigates each anomaly, computes merchant/provider context, generates a human-readable case report with recommendations, and logs it for review.

## What Changes

- **Add LangGraph investigation agent** — a linear graph (`gather_context → analyze_patterns → generate_report → log_alert`) that runs in a background thread, consuming scored AnomalyEvents from an investigation bus
- **Add investigation bus** — new EventBus instance bridging the anomaly scorer to the agent; the scorer publishes scored AnomalyEvents (score >= 0.85 or DRIFT) to this bus
- **Add merchant/provider context computation** — calculates historical failure rate, average latency, and provider-wide correlation from in-memory Phase 1/2 data (matched_pairs, anomaly_events)
- **Add case report model and storage** — `CaseReport` Pydantic model capturing severity, pattern classification, merchant/provider stats, LLM recommendation, and investigation metadata; stored in-memory
- **Add LLM-generated case reports** — pluggable LLM via `langchain`'s `init_chat_model()` to synthesize investigation findings into actionable recommendations; mock mode for testing
- **Add alert logging** — log-only alert output for MVP (no real Slack); structured log entries with full case report for each investigation
- **Add investigation API endpoints** — `GET /cases` to list case reports, `GET /cases/{case_id}` to retrieve a specific report, `GET /cases/stats` for investigation statistics
- **Add investigation configuration** — new settings for LLM model name, investigation bus size, lookback window, and agent enable/disable toggle

## Capabilities

### New Capabilities
- `agent-investigation`: LangGraph-based autonomous anomaly investigation with merchant/provider context, pattern analysis, LLM case report generation, and alert logging

### Modified Capabilities
- `anomaly-detection`: AnomalyScorer publishes scored events to investigation bus in addition to internal collection

## Impact

- **New module** (`src/hybrid_sentinel/agent/`): graph, nodes, state, context computation, alert logging
- **Models** (`src/hybrid_sentinel/models.py`): new `CaseReport` model
- **Scorer** (`src/hybrid_sentinel/anomaly/scorer.py`): publishes to investigation bus when score >= threshold or DRIFT detected
- **Config** (`src/hybrid_sentinel/config.py`): new agent investigation settings
- **Routes**: new `/cases` endpoint group
- **Main** (`src/hybrid_sentinel/main.py`): agent start/stop in lifespan
- **Dependencies** (`pyproject.toml`): `langgraph`, `langchain`, `langchain-core` packages
