## 1. Data Model Updates

- [x] 1.1 Add `actual_amount: Decimal = Field(..., gt=0)` field to `CallbackEvent` model in `src/hybrid_sentinel/models.py`
- [x] 1.2 Add `actual_currency: str = Field(..., min_length=3, max_length=3)` field to `CallbackEvent` model
- [x] 1.3 Verify Pydantic validation requires both fields and rejects callbacks missing either field

## 2. Unit Tests — Model Validation

- [x] 2.1 Add test for valid `CallbackEvent` with `actual_amount` and `actual_currency` — expect success
- [x] 2.2 Add test for `CallbackEvent` missing `actual_amount` — expect validation error
- [x] 2.3 Add test for `CallbackEvent` missing `actual_currency` — expect validation error
- [x] 2.4 Add test for invalid `actual_currency` length (e.g., `"US"` or `"DOLLAR"`) — expect validation error
- [x] 2.5 Add test for zero or negative `actual_amount` — expect validation error

## 3. Unit Tests — Webhook Endpoint

- [x] 3.1 Add test for webhook accepting callback with valid `actual_amount` and `actual_currency` — expect 202 Accepted
- [x] 3.2 Add test for webhook rejecting callback missing `actual_amount` — expect 422 Unprocessable Entity
- [x] 3.3 Add test for webhook rejecting callback missing `actual_currency` — expect 422 Unprocessable Entity
- [x] 3.4 Add test for webhook rejecting callback with invalid `actual_currency` (wrong length) — expect 422

## 4. Integration Tests

- [x] 4.1 Add integration test: submit transaction with amount/currency, then callback with **different** `actual_amount`/`actual_currency` → verify `MatchedPair` contains both original transaction values and actual callback values
- [x] 4.2 Add integration test: submit transaction, then callback with **same** `actual_amount`/`actual_currency` → verify `MatchedPair` contains matching values

## 5. Documentation Updates

- [x] 5.1 Update `docs/stream-processing.md` — add `actual_amount` and `actual_currency` to CallbackEvent field list with descriptions
- [x] 5.2 Update `docs/stream-processing.md` — add example callback JSON with new required fields in API Reference section
- [x] 5.3 Update `docs/stream-processing.md` — add reconciliation use case note explaining how actual amount/currency differs from requested amount/currency

## 6. Verification

- [x] 6.1 Run `ruff check src/ tests/` — verify no linting errors
- [x] 6.2 Run `mypy src/` — verify type checking passes
- [x] 6.3 Run `pytest tests/` — verify all tests pass (including new validation tests)
