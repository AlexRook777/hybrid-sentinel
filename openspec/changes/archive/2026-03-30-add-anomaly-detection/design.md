## Context

Phase 1 delivers a working Bytewax stream that pairs transactions with callbacks and emits TIMEOUT anomalies. The stream sink currently collects events in thread-safe in-memory lists (`matched_pairs[]`, `anomaly_events[]`). There is no scoring, no ML, and no way to distinguish genuine threats from noise.

The payment gateway processes ~180K transactions/day with a target of 1K–10K TPS. Anomaly detection must score events within <10 seconds of arrival without batch retraining — the definition of "normal" shifts daily as merchant behavior and provider reliability evolve.

River (Python online ML library) is already a project decision. The event bus pattern established in Phase 1 provides a natural integration point.

## Goals / Non-Goals

**Goals:**
- Score every MatchedPair and TIMEOUT event with a 0.0–1.0 anomaly score using River
- Detect concept drift per-merchant via ADWIN on failure rate and callback latency
- Emit scored AnomalyEvents onto a scoring bus for Phase 3 consumption
- Remain silent during model warmup to avoid false positives
- Provide an observability endpoint for model state and drift status

**Non-Goals:**
- Persisting model state to disk (in-memory is sufficient for Phase 2; persistence is Phase 3+)
- Per-merchant ML models (global model + per-merchant drift detectors instead)
- Custom anomaly thresholds per type (single 0.85 threshold for all)
- Database or external storage for scored events (in-memory collection, same pattern as Phase 1)
- Integration with LangGraph agent (that's Phase 3)

## Decisions

### D1: Event Bus Subscriber Pattern (not inline Bytewax)

The anomaly scorer runs as an independent subscriber to a scoring bus, not as a `map` step inside the Bytewax dataflow.

**Why**: Decoupling keeps stream processing and ML as separate concerns. The scorer can be tested, replaced, or scaled independently. Bytewax stateful operators have serialization constraints that complicate River model state.

**Alternative considered**: Inline River scoring in Bytewax `stateful_map`. Rejected because it couples two complex systems and makes unit testing harder.

**Implementation**: The Bytewax sink publishes events to a `ScoringBus` (same `EventBus` class, new instance). The `AnomalyScorer` runs in its own background thread, consuming from the scoring bus.

### D2: River HalfSpaceTrees as Anomaly Model

Use `river.anomaly.HalfSpaceTrees` — the standard streaming anomaly detector in River.

**Why**: Purpose-built for online anomaly detection. O(1) memory, O(tree_depth) per update, no windowing needed. Produces scores in [0, 1] range. Handles high-dimensional feature vectors without preprocessing.

**Alternative considered**: `river.anomaly.OneClassSVM` — higher accuracy on some distributions but O(n) with support vectors, unsuitable for high-throughput streaming. Ensemble approach deferred to future optimization.

**Parameters**: `n_trees=15`, `height=6`, `window_size=500` (tunable via config). These are River defaults and work well for moderate-dimensional data.

### D3: Global Model + Per-Merchant ADWIN Drift Detectors

One global HalfSpaceTrees model learns "normal" across all merchants/providers. Per-merchant `ADWIN` detectors monitor failure rate and callback latency.

**Why**: A global model avoids cold-start problems per merchant — new merchants benefit from the model immediately. ADWIN per merchant catches merchant-specific behavioral shifts (e.g., a single merchant's failure rate spikes) that the global model might absorb as noise.

**Alternative considered**: Fully per-merchant models. Rejected due to cold-start delays (each new merchant needs ~1000 events before scoring) and memory overhead (one HalfSpaceTrees per merchant).

**ADWIN tracked metrics**: `failure_rate` (rolling), `callback_latency_seconds` (rolling). When ADWIN detects a drift, a `DRIFT` anomaly event is emitted regardless of model warmup state.

### D4: Silent Warmup (No Scores Until N Events)

The scorer does not emit AnomalyEvents until `model_warmup_events` (default 1000) events have been processed. During warmup, the model learns but produces no output.

**Why**: HalfSpaceTrees needs sufficient data to calibrate what "normal" looks like. Early scores are unreliable and would flood Phase 3 with false positives.

**Exception**: ADWIN drift detectors also observe a silent period. However, TIMEOUT anomalies from Phase 1 are still logged (they pass through with no River score attached) — Phase 1 TIMEOUTs are deterministic, not ML-dependent.

### D5: Feature Extraction (~12 Features)

Features are extracted from MatchedPair and TIMEOUT events into a `dict[str, float]` for River (River uses dicts, not numpy arrays).

| Feature | Source | Type |
|---------|--------|------|
| `amount_log` | log(transaction.amount) | Continuous |
| `callback_latency_s` | callback.timestamp − transaction.timestamp | Continuous |
| `is_success` | callback.status == "success" | Binary (0/1) |
| `is_failure` | callback.status == "failure" | Binary (0/1) |
| `is_amount_mismatch` | actual_amount ≠ expected amount | Binary (0/1) |
| `amount_mismatch_pct` | abs(actual − expected) / expected × 100 | Continuous |
| `hour_of_day` | transaction.timestamp.hour / 24 | Normalized [0, 1) |
| `day_of_week` | transaction.timestamp.weekday() / 7 | Normalized [0, 1) |
| `is_round_amount` | amount % 100 == 0 | Binary (0/1) |
| `provider_hash` | hash(provider_id) % 64 | Categorical bucket |
| `merchant_hash` | hash(merchant_id) % 64 | Categorical bucket |
| `is_timeout` | 1 if TIMEOUT event | Binary (0/1) |

For TIMEOUT events (no callback data): `callback_latency_s=300`, `is_success=0`, `is_failure=0`, `is_amount_mismatch=0`, `amount_mismatch_pct=0`.

### D6: Anomaly Type Classification

After River scores an event, the scorer classifies it into a specific anomaly type based on which features contributed most:

| Type | Condition |
|------|-----------|
| `TIMEOUT` | Source event was a Phase 1 TIMEOUT (passthrough, now scored) |
| `AMOUNT_MISMATCH` | `amount_mismatch_pct > 10` and score ≥ 0.85 |
| `LATENCY_SPIKE` | `callback_latency_s > 3 × rolling_mean` and score ≥ 0.85 |
| `DRIFT` | ADWIN detects drift on merchant's failure_rate or latency |
| `BEHAVIORAL` | Score ≥ 0.85 and no specific sub-type matches (catch-all) |

### D7: Module Structure

```
src/hybrid_sentinel/anomaly/
├── __init__.py          # Public API: AnomalyScorer, start_scorer, stop_scorer
├── scorer.py            # Main AnomalyScorer class (thread, bus consumer)
├── features.py          # Feature extraction from MatchedPair / AnomalyEvent
├── drift.py             # Per-merchant ADWIN drift detection
└── classify.py          # Anomaly type classification from score + features
```

The scorer lifecycle is managed via the FastAPI lifespan (same pattern as Bytewax dataflow).

## Risks / Trade-offs

**[Cold-start detection gap]** → During the first ~1000 events after startup, the system cannot detect behavioral anomalies. Mitigation: Phase 1 TIMEOUT detection is still active (deterministic, no warmup needed). ADWIN drift detectors also have a warmup period but activate faster (~100 observations).

**[Hash collision in categorical features]** → `provider_hash` and `merchant_hash` use modulo 64, so different providers may hash to the same bucket. Mitigation: Acceptable for anomaly detection — the model learns patterns, not identities. If precision suffers, increase bucket count.

**[Single global model may miss merchant-specific anomalies]** → A merchant with unusual but consistent behavior (e.g., always large amounts) may look normal globally. Mitigation: Per-merchant ADWIN detectors catch shifts in individual merchant behavior, complementing the global model.

**[Memory growth in drift detectors]** → One ADWIN instance per merchant × 2 metrics = 2 × N_merchants. Mitigation: ADWIN is memory-efficient (logarithmic in window size). For 10K merchants, memory is ~20–40MB — well within limits.

**[Thread safety between scorer and API]** → The scorer runs in a background thread while the API reads stats. Mitigation: Use threading lock for shared state (same pattern as Phase 1 sink).
