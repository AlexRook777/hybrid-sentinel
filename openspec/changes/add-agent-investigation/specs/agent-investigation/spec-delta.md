## ADDED Requirements

### Requirement: Investigation Bus
WHEN the anomaly scorer emits a scored AnomalyEvent (score >= threshold) or a DRIFT AnomalyEvent,
the system SHALL publish the event to an investigation bus (EventBus instance) for consumption by the investigation agent.

#### Scenario: Scored anomaly published to investigation bus
- **GIVEN** the anomaly scorer has emitted an AnomalyEvent with `anomaly_score` >= 0.85
- **WHEN** the scorer processes the event
- **THEN** the AnomalyEvent is enqueued on the investigation bus
- **AND** the scorer does not block if the investigation bus is full

#### Scenario: DRIFT anomaly published to investigation bus
- **GIVEN** the anomaly scorer has emitted a DRIFT AnomalyEvent
- **WHEN** the scorer processes the event
- **THEN** the DRIFT AnomalyEvent is enqueued on the investigation bus

#### Scenario: Investigation bus full does not block scorer
- **GIVEN** the investigation bus queue is at capacity
- **WHEN** the scorer attempts to publish an AnomalyEvent
- **THEN** a warning is logged that the investigation event was dropped
- **AND** the scorer continues processing without blocking

### Requirement: LangGraph Investigation Graph
WHEN an AnomalyEvent is dequeued from the investigation bus,
the system SHALL execute a linear LangGraph investigation pipeline consisting of `gather_context`, `analyze_patterns`, `generate_report`, and `log_alert` nodes.

#### Scenario: Full investigation pipeline executes
- **GIVEN** an AnomalyEvent with `anomaly_score` 0.92 and `merchant_id` "M1" is on the investigation bus
- **WHEN** the agent dequeues the event
- **THEN** the graph executes all four nodes in order: gather_context → analyze_patterns → generate_report → log_alert
- **AND** a CaseReport is produced and stored in the in-memory case report list

#### Scenario: Investigation handles missing merchant data gracefully
- **GIVEN** an AnomalyEvent for a merchant with no historical matched pairs
- **WHEN** the gather_context node executes
- **THEN** merchant stats are returned with `failure_rate` 0.0, `avg_latency` 0.0, and `event_count` 0
- **AND** the investigation continues through all remaining nodes

### Requirement: Merchant Context Computation
WHEN the gather_context node executes,
the system SHALL compute merchant historical statistics from the in-memory matched_pairs list filtered by the anomaly's `merchant_id`.

#### Scenario: Merchant failure rate computed correctly
- **GIVEN** merchant "M1" has 100 matched pairs, of which 15 have callback status "failure"
- **WHEN** merchant stats are computed for "M1"
- **THEN** `merchant_failure_rate` is 0.15

#### Scenario: Merchant average latency computed correctly
- **GIVEN** merchant "M1" has 3 matched pairs with callback latencies of 1.0s, 2.0s, and 3.0s
- **WHEN** merchant stats are computed for "M1"
- **THEN** `merchant_avg_latency` is 2.0

#### Scenario: Merchant event count reflects total pairs
- **GIVEN** merchant "M1" has 50 matched pairs in the in-memory list
- **WHEN** merchant stats are computed for "M1"
- **THEN** `merchant_event_count` is 50

### Requirement: Provider Context Computation
WHEN the gather_context node executes,
the system SHALL compute provider statistics from the in-memory matched_pairs list filtered by the anomaly's `provider_id` within the configured lookback window.

#### Scenario: Provider failure rate computed within lookback window
- **GIVEN** provider "P1" has 200 matched pairs within the last 10 minutes, of which 30 have callback status "failure"
- **WHEN** provider stats are computed for "P1" with a 10-minute lookback
- **THEN** `provider_failure_rate` is 0.15

#### Scenario: Provider affected merchants counted correctly
- **GIVEN** provider "P1" has failures for merchants "M1", "M2", and "M3" within the lookback window
- **WHEN** provider stats are computed for "P1"
- **THEN** `provider_affected_merchants` is 3

#### Scenario: Provider total merchants counted correctly
- **GIVEN** provider "P1" has matched pairs for merchants "M1", "M2", "M3", and "M4" within the lookback window
- **WHEN** provider stats are computed for "P1"
- **THEN** `provider_total_merchants` is 4

#### Scenario: Events outside lookback window are excluded
- **GIVEN** provider "P1" has 50 matched pairs from 20 minutes ago and 10 from the last 10 minutes
- **WHEN** provider stats are computed with a 10-minute lookback
- **THEN** only the 10 recent pairs are used for computation

### Requirement: Pattern Classification
WHEN the analyze_patterns node executes,
the system SHALL classify the anomaly into one of the following patterns based on merchant and provider context: `provider_outage`, `merchant_targeting`, `timeout_cluster`, or `behavioral`.

#### Scenario: Provider outage detected
- **GIVEN** `provider_affected_merchants` >= 3 AND `provider_failure_rate` > 0.10
- **WHEN** pattern classification runs
- **THEN** the pattern is set to `provider_outage`

#### Scenario: Merchant targeting detected
- **GIVEN** `merchant_failure_rate` > 5x the provider-wide failure rate AND `provider_affected_merchants` <= 1
- **WHEN** pattern classification runs
- **THEN** the pattern is set to `merchant_targeting`

#### Scenario: Timeout cluster detected
- **GIVEN** the anomaly type is "TIMEOUT" AND `provider_failure_rate` > 0.05
- **WHEN** pattern classification runs
- **THEN** the pattern is set to `timeout_cluster`

#### Scenario: Behavioral catch-all
- **GIVEN** the anomaly does not match provider_outage, merchant_targeting, or timeout_cluster conditions
- **WHEN** pattern classification runs
- **THEN** the pattern is set to `behavioral`

### Requirement: Severity Assignment
WHEN the analyze_patterns node classifies a pattern,
the system SHALL assign a severity level of `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.

#### Scenario: Critical severity for large provider outage
- **GIVEN** the pattern is `provider_outage` AND `provider_affected_merchants` >= 5
- **WHEN** severity is assigned
- **THEN** the severity is `CRITICAL`

#### Scenario: High severity for provider outage or merchant targeting
- **GIVEN** the pattern is `provider_outage` (with affected_merchants < 5) OR `merchant_targeting`
- **WHEN** severity is assigned
- **THEN** the severity is `HIGH`

#### Scenario: Medium severity for timeout cluster or very high score
- **GIVEN** the pattern is `timeout_cluster` OR the anomaly score is >= 0.95
- **WHEN** severity is assigned
- **THEN** the severity is `MEDIUM`

#### Scenario: Low severity for behavioral catch-all
- **GIVEN** the pattern is `behavioral` AND the anomaly score is < 0.95
- **WHEN** severity is assigned
- **THEN** the severity is `LOW`

### Requirement: LLM Case Report Generation
WHEN the generate_report node executes,
the system SHALL produce a recommendation string using a LangChain-compatible LLM or a template-based fallback.

#### Scenario: LLM generates recommendation
- **GIVEN** `SENTINEL_AGENT_LLM_MODEL` is set to a valid model name (e.g., "gpt-4o")
- **WHEN** the generate_report node executes with gathered context and pattern analysis
- **THEN** the LLM is invoked with a prompt containing the anomaly details, merchant stats, provider stats, and pattern
- **AND** the LLM response is stored as the recommendation

#### Scenario: Mock mode uses template-based report
- **GIVEN** `SENTINEL_AGENT_LLM_MODEL` is empty or set to "mock"
- **WHEN** the generate_report node executes
- **THEN** a template-based recommendation is generated without calling any external LLM
- **AND** the recommendation includes the pattern, severity, and key statistics

#### Scenario: LLM failure falls back to template
- **GIVEN** `SENTINEL_AGENT_LLM_MODEL` is set to a valid model name but the API key is missing or the call fails
- **WHEN** the generate_report node executes
- **THEN** the system falls back to a template-based recommendation
- **AND** a warning is logged about the LLM failure

### Requirement: CaseReport Model
WHEN an investigation completes,
the system SHALL produce a CaseReport containing the anomaly event, severity, pattern, merchant stats, provider stats, recommendation, investigation duration, and timestamp.

#### Scenario: CaseReport contains all required fields
- **WHEN** an investigation completes for an AnomalyEvent
- **THEN** the CaseReport includes: `case_id` (UUID), `anomaly_event`, `severity`, `pattern`, `merchant_failure_rate`, `merchant_avg_latency`, `merchant_event_count`, `provider_failure_rate`, `provider_affected_merchants`, `recommendation`, `investigation_duration_ms`, and `timestamp`

#### Scenario: CaseReport stored in-memory
- **WHEN** an investigation completes and produces a CaseReport
- **THEN** the CaseReport is appended to the in-memory case report list
- **AND** it is retrievable via the API

### Requirement: Alert Logging
WHEN the log_alert node executes,
the system SHALL log a structured alert with the full case report details.

#### Scenario: Structured log entry for completed investigation
- **WHEN** a case report is generated with severity "HIGH" and pattern "provider_outage"
- **THEN** a structured log entry is emitted at INFO level containing the case_id, severity, pattern, merchant_id, provider_id, and recommendation summary

#### Scenario: Log-only output (no external notifications)
- **WHEN** the log_alert node executes
- **THEN** the alert is written only to the application log
- **AND** no external services (Slack, email, etc.) are contacted

### Requirement: Investigation Agent Lifecycle
WHEN the application starts,
the system SHALL initialize and run the investigation agent in a background thread alongside the anomaly scorer.

#### Scenario: Agent starts with application
- **GIVEN** the FastAPI application is starting via its lifespan handler
- **WHEN** the lifespan startup completes
- **THEN** the investigation agent background thread is running
- **AND** it is consuming from the investigation bus

#### Scenario: Agent stops with application
- **GIVEN** the investigation agent is running
- **WHEN** the FastAPI application shuts down
- **THEN** the agent thread is signaled to stop
- **AND** the thread joins within a reasonable timeout

#### Scenario: Agent disabled via configuration
- **GIVEN** `SENTINEL_AGENT_ENABLED` is set to False
- **WHEN** the application starts
- **THEN** the investigation agent is not started
- **AND** the investigation bus is not created

### Requirement: Investigation API Endpoints
The system SHALL expose API endpoints for retrieving case reports and investigation statistics.

#### Scenario: List all case reports
- **WHEN** a GET request is made to `/cases`
- **THEN** the response contains a JSON array of all case reports, ordered by timestamp descending

#### Scenario: Retrieve a specific case report
- **GIVEN** a case report with `case_id` "abc-123" exists
- **WHEN** a GET request is made to `/cases/abc-123`
- **THEN** the response contains the full CaseReport as JSON

#### Scenario: Case report not found
- **GIVEN** no case report with `case_id` "nonexistent" exists
- **WHEN** a GET request is made to `/cases/nonexistent`
- **THEN** the response is HTTP 404

#### Scenario: Investigation statistics
- **GIVEN** the agent has completed 10 investigations (3 CRITICAL, 5 HIGH, 2 LOW)
- **WHEN** a GET request is made to `/cases/stats`
- **THEN** the response contains `total_investigations`, `cases_by_severity`, `cases_by_pattern`, and `agent_enabled` status

### Requirement: Investigation Configuration
The system SHALL expose configurable settings for the investigation agent, loaded from environment variables with the `SENTINEL_` prefix.

#### Scenario: Default configuration values
- **WHEN** no environment variables are set for the investigation agent
- **THEN** `agent_enabled` defaults to True
- **AND** `agent_llm_model` defaults to "mock"
- **AND** `agent_lookback_minutes` defaults to 10
- **AND** `investigation_queue_max_size` defaults to 1000

#### Scenario: Custom LLM model via environment
- **GIVEN** the environment variable `SENTINEL_AGENT_LLM_MODEL` is set to "gpt-4o"
- **WHEN** the application starts
- **THEN** the investigation agent uses `init_chat_model("gpt-4o")` to instantiate the LLM

#### Scenario: Agent disabled via environment
- **GIVEN** the environment variable `SENTINEL_AGENT_ENABLED` is set to "false"
- **WHEN** the application starts
- **THEN** the investigation agent is not started
