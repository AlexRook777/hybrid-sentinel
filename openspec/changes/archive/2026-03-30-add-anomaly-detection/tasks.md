## 1. Dependencies & Configuration

- [x] 1.1 Add `river` dependency to pyproject.toml
- [x] 1.2 Add anomaly detection settings to `config.py`: `anomaly_threshold` (0.85), `model_warmup_events` (1000), `drift_detection_enabled` (True), `scoring_queue_max_size` (10000), `hst_n_trees` (15), `hst_height` (6), `hst_window_size` (500)

## 2. Data Model Extensions

- [x] 2.1 Add optional `anomaly_score: float | None` field to `AnomalyEvent` in `models.py` (default None)
- [x] 2.2 Add tests verifying Phase 1 TIMEOUT events have `anomaly_score=None` and Phase 2 scored events have a float value

## 3. Scoring Bus

- [x] 3.1 Create scoring bus instance (reuse `EventBus` class) in `src/hybrid_sentinel/anomaly/__init__.py`
- [x] 3.2 Modify `stream/sink.py` to publish MatchedPair and AnomalyEvent to the scoring bus (non-blocking, log on drop)
- [x] 3.3 Add tests verifying sink publishes to scoring bus and handles full-queue gracefully

## 4. Feature Extraction

- [x] 4.1 Create `src/hybrid_sentinel/anomaly/features.py` with `extract_features(event: MatchedPair | AnomalyEvent) -> dict[str, float]` implementing all 12 features
- [x] 4.2 Add tests for feature extraction from MatchedPair (normal case, amount mismatch, failure)
- [x] 4.3 Add tests for feature extraction from TIMEOUT AnomalyEvent (sentinel values)
- [x] 4.4 Add tests for temporal feature normalization (hour_of_day, day_of_week)

## 5. Anomaly Type Classification

- [x] 5.1 Create `src/hybrid_sentinel/anomaly/classify.py` with `classify_anomaly(event, features, score, rolling_latency_mean) -> str` returning anomaly type
- [x] 5.2 Add tests for each classification path: TIMEOUT, AMOUNT_MISMATCH, LATENCY_SPIKE, BEHAVIORAL

## 6. Concept Drift Detection

- [x] 6.1 Create `src/hybrid_sentinel/anomaly/drift.py` with `DriftDetectorManager` using per-merchant ADWIN on failure_rate and callback_latency
- [x] 6.2 Add `update(merchant_id, is_failure, latency) -> list[DriftAlert]` method that returns drift alerts when ADWIN triggers
- [x] 6.3 Add tests for drift detection: stable behavior (no alert), failure rate shift (alert), latency shift (alert)

## 7. Anomaly Scorer (Core)

- [x] 7.1 Create `src/hybrid_sentinel/anomaly/scorer.py` with `AnomalyScorer` class: initializes HalfSpaceTrees model, tracks warmup count, consumes from scoring bus in a loop
- [x] 7.2 Implement `score_event` method: extract features → score with model → learn → classify → emit AnomalyEvent if score ≥ threshold and past warmup
- [x] 7.3 Implement scored event collection (thread-safe list, same pattern as Phase 1 sink)
- [x] 7.4 Implement `get_stats()` method returning warmup status, events processed, anomalies emitted, drift detector count
- [x] 7.5 Add tests for warmup behavior: no emissions during warmup, emissions start after threshold
- [x] 7.6 Add tests for scoring and threshold gating: below-threshold not emitted, above-threshold emitted, exact threshold emitted
- [x] 7.7 Add tests for drift event emission independent of warmup

## 8. Scorer Lifecycle & API

- [x] 8.1 Add `start_scorer()` and `stop_scorer()` functions to `anomaly/__init__.py` managing the background thread
- [x] 8.2 Wire scorer start/stop into FastAPI lifespan in `main.py` (after Bytewax dataflow start)
- [x] 8.3 Create `routes/anomalies.py` with `GET /anomalies/stats` endpoint returning scorer stats
- [x] 8.4 Register anomaly routes in `main.py`
- [x] 8.5 Add tests for `/anomalies/stats` endpoint (warmup state, post-warmup state)

## 9. Integration Tests

- [x] 9.1 Add end-to-end test: ingest transaction + callback via webhook → Bytewax matches → scoring bus receives → scorer processes → verify feature extraction and model update
- [x] 9.2 Add end-to-end test: ingest transaction with no callback → TIMEOUT → scoring bus receives → scorer handles TIMEOUT event
