## Why

Phase 1 (stream processing) produces matched transaction-callback pairs and TIMEOUT anomalies, but has no intelligence to distinguish normal behavior from genuine threats. Every TIMEOUT is flagged equally — whether it's a transient network hiccup or a systemic provider failure. The system cannot detect behavioral anomalies like unusual transaction amounts, latency spikes, abnormal failure rates, or amount mismatches that signal fraud, BIN attacks, or provider degradation.

Phase 2 adds an online ML scoring layer using River that learns incrementally from every event, detects concept drift as "normal" evolves, and produces anomaly scores that trigger Phase 3 (agent investigation) when they exceed the 0.85 threshold.

## What Changes

- **Add River-based anomaly scoring pipeline** — a standalone scorer that subscribes to stream output via the event bus, extracts features from MatchedPair and TIMEOUT events, scores them with HalfSpaceTrees, and emits scored AnomalyEvents
- **Add feature extraction module** — transforms raw MatchedPair/AnomalyEvent data into ~12 numerical features (amount, latency, status, temporal patterns, provider/merchant encoding)
- **Add ADWIN concept drift detection** — per-merchant drift detectors on failure rate and callback latency that flag behavioral shifts independently of the anomaly score
- **Add silent warmup mode** — the scorer does not emit anomaly events until the model has processed a configurable number of events (default 1000), preventing false positives from an untrained model
- **Extend AnomalyEvent model** — add `anomaly_score` (float 0.0–1.0) field and new `anomaly_type` values: `BEHAVIORAL`, `AMOUNT_MISMATCH`, `LATENCY_SPIKE`, `DRIFT`, and `TIMEOUT` (now with score)
- **Add anomaly detection configuration** — new settings for threshold (0.85), warmup count, drift detection toggle, and model parameters
- **Add anomaly detection API endpoint** — `GET /anomalies/stats` for observability into model state, warmup progress, and drift status

## Capabilities

### New Capabilities
- `anomaly-detection`: Online ML anomaly scoring with River (HalfSpaceTrees), feature extraction, concept drift detection (ADWIN), silent warmup, and scored anomaly event emission

### Modified Capabilities
- `stream-processing`: AnomalyEvent model gains `anomaly_score` field; stream sink is extended to publish events to a scoring bus in addition to collection

## Impact

- **Models** (`src/hybrid_sentinel/models.py`): AnomalyEvent extended with `anomaly_score: float` field
- **New module** (`src/hybrid_sentinel/anomaly/`): scorer, features, drift detector, config
- **Stream sink** (`src/hybrid_sentinel/stream/sink.py`): publishes MatchedPair/AnomalyEvent to scoring bus
- **Config** (`src/hybrid_sentinel/config.py`): new anomaly detection settings
- **Routes**: new `/anomalies/stats` endpoint
- **Dependencies** (`pyproject.toml`): `river` package added
- **Tests**: new test suite for feature extraction, scoring, drift detection, warmup behavior
