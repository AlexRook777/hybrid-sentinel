## Why

Payment providers allow payers to change the transaction amount and/or currency within their payment widget. Currently, our CallbackEvent model only captures the payment status but not the actual amount and currency that was charged. This creates a reconciliation gap where we can't detect when the paid amount differs from the originally requested amount, which is critical for fraud detection, revenue tracking, and dispute resolution.

## What Changes

- Add `actual_amount` field to CallbackEvent model (Decimal, **required**)
- Add `actual_currency` field to CallbackEvent model (str, **required**)
- Update webhook endpoint validation to require these fields in callback payloads
- Update tests to cover scenarios where actual amount/currency differs from transaction amount/currency
- Update documentation to reflect the new required fields and their reconciliation use cases

## Capabilities

### New Capabilities
<!-- None - this is a modification to existing capabilities -->

### Modified Capabilities
- `stream-processing`: CallbackEvent data model will include actual_amount and actual_currency fields
- `api-ingestion`: Webhook endpoint will validate and accept actual_amount and actual_currency in callback payloads

## Impact

**Code**:
- `src/hybrid_sentinel/models.py` — CallbackEvent model
- `tests/test_models.py` — Model validation tests
- `tests/test_webhooks.py` — Webhook endpoint tests
- `docs/stream-processing.md` — API documentation

**APIs**:
- `POST /webhooks/transaction` — **BREAKING**: Callback payloads now require `actual_amount` and `actual_currency` fields

**Dependencies**:
- No new dependencies required

**Breaking Changes**:
- Callbacks without `actual_amount` and `actual_currency` will be rejected with 422 (not in production yet, safe to make breaking change)
