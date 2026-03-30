## Context

Currently, `CallbackEvent` includes `status` but not the actual charged amount and currency. Payment providers (Stripe, PayPal, etc.) allow payers to modify amounts within their payment widgets. For example:
- Merchant requests $100 USD
- Payer changes to €90 EUR in the provider widget
- Provider sends callback with `status: "success"` but no amount/currency

This gap prevents:
- **Reconciliation**: Can't verify actual revenue vs. expected revenue
- **Fraud detection**: Can't flag when paid amount ≠ intended amount
- **Dispute resolution**: Missing audit trail for amount mismatches

**Current State**:
```python
class CallbackEvent:
    merchant_id: str
    transaction_id: str
    status: Literal["success", "failure", "pending"]
    provider_id: str
    timestamp: datetime
```

**Note**: This application is not yet in production, so we can make breaking changes without backward compatibility concerns.

## Goals / Non-Goals

**Goals:**
- Add **required** `actual_amount` and `actual_currency` fields to `CallbackEvent`
- Ensure payment providers always send the actual charged amount and currency
- Enable amount/currency reconciliation in future phases (Phase 2: River scoring)

**Non-Goals:**
- Automatic reconciliation logic (Phase 2 concern)
- Rejecting callbacks when actual amount ≠ transaction amount
- Currency conversion logic
- Backward compatibility (not needed — pre-production)

## Decisions

### 1. Fields are required (not optional)

**Decision**: `actual_amount` and `actual_currency` are both **required** fields.

**Alternatives considered**:
- **Optional fields**: Would allow incomplete data, defeating the reconciliation purpose.

**Rationale**: Since we're pre-production, we can enforce complete data from the start. Every callback must include the actual amount and currency that was charged. This guarantees we can always reconcile transactions.

### 2. Use Decimal (not float) for actual_amount

**Decision**: `actual_amount: Decimal = Field(..., gt=0)` (consistent with `TransactionEvent.amount`).

**Rationale**: Already using `Decimal` for `TransactionEvent.amount` (fixed in Phase 1 code review). Consistency across models, financial precision.

### 3. Currency validation: 3-character constraint

**Decision**: `actual_currency: str = Field(..., min_length=3, max_length=3)`.

**Alternatives considered**:
- **No validation**: Could allow invalid currencies like `"US"` or `"DOLLAR"`.
- **ISO 4217 enum**: Too strict, hard to maintain, providers might use custom codes.

**Rationale**: Same validation as `TransactionEvent.currency`. Balances strictness (prevents typos) with flexibility (allows non-ISO codes if provider uses them).

### 4. No automatic reconciliation alerts in Phase 1

**Decision**: Stream processor does NOT compare `actual_amount` vs `transaction.amount`. Just stores the values in `MatchedPair`.

**Rationale**: Reconciliation is a Phase 2 (River ML) concern. Phase 1 focuses on data collection. Adding comparison logic now would blur phase boundaries.

## Risks / Trade-offs

**[Risk]**: Providers might send `actual_amount` in a different currency unit (cents vs. dollars)
- **Mitigation**: Document expected format in API docs. Rely on `actual_currency` to interpret units. In practice, providers standardize on decimal amounts (e.g., Stripe sends `100.50`, not `10050` cents).

**[Trade-off]**: Requiring fields makes the API stricter
- **Benefit**: Guarantees complete data for reconciliation.
- **Cost**: Webhook integrations must provide both fields (acceptable since pre-production).

**[Trade-off]**: MatchedPair grows larger (more fields to serialize)
- **Impact**: Negligible. Two required fields add ~50 bytes per matched pair. At 180K pairs/day, that's ~9 MB/day.

## Migration Plan

**Deployment**:
1. Deploy updated models and webhook endpoint
2. Update documentation showing required `actual_amount`/`actual_currency` fields
3. Update integration tests to always include these fields

**Rollback**:
- If issues arise, revert the model change
- No database migration needed (in-memory stream processing)

**Testing**:
- Unit tests: Validate CallbackEvent requires both fields
- Unit tests: Reject callbacks missing either field (422 error)
- Integration tests: Submit callbacks with mismatched amounts, verify MatchedPair contains both transaction and callback amounts
