"""Unit tests for the stream processor (callback matching + timeout)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hybrid_sentinel.models import (
    AnomalyEvent,
    CallbackEvent,
    MatchedPair,
    TransactionEvent,
)
from hybrid_sentinel.stream.processor import (
    CallbackMatcherState,
    TickEvent,
    callback_matcher,
    clear_active_keys,
    get_active_keys,
)


def _make_transaction(
    merchant_id: str = "M1",
    transaction_id: str = "T100",
) -> TransactionEvent:
    return TransactionEvent(
        merchant_id=merchant_id,
        transaction_id=transaction_id,
        amount=Decimal("100.00"),
        currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )


def _make_callback(
    merchant_id: str = "M1",
    transaction_id: str = "T100",
    status: str = "success",
) -> CallbackEvent:
    return CallbackEvent(
        merchant_id=merchant_id,
        transaction_id=transaction_id,
        status=status,
        actual_amount=Decimal("100.00"),
        actual_currency="USD",
        provider_id="P1",
        timestamp=datetime.now(UTC),
    )


class TestCallbackMatcherState:
    """Tests for CallbackMatcherState directly."""

    def setup_method(self) -> None:
        clear_active_keys()

    def test_transaction_stored_in_state(self) -> None:
        state = CallbackMatcherState()
        txn = _make_transaction()
        state, outputs = state.process_event(txn)

        assert len(outputs) == 0
        assert "M1:T100" in state.pending_transactions
        assert "M1:T100" in get_active_keys()

    def test_callback_matches_pending_transaction(self) -> None:
        state = CallbackMatcherState()
        txn = _make_transaction()
        state, _ = state.process_event(txn)

        cb = _make_callback()
        state, outputs = state.process_event(cb)

        assert len(outputs) == 1
        assert isinstance(outputs[0], MatchedPair)
        assert outputs[0].transaction.transaction_id == "T100"
        assert outputs[0].callback.status == "success"
        assert "M1:T100" not in state.pending_transactions
        assert "M1:T100" not in get_active_keys()

    def test_orphaned_callback_produces_no_output(self) -> None:
        state = CallbackMatcherState()
        cb = _make_callback(merchant_id="M1", transaction_id="T999")
        state, outputs = state.process_event(cb)

        assert len(outputs) == 0
        assert len(state.pending_transactions) == 0

    def test_callback_before_timeout(self) -> None:
        """Callback arriving before timeout produces matched pair, no anomaly."""
        state = CallbackMatcherState()
        txn = _make_transaction()
        state, _ = state.process_event(txn)

        # Check timeouts — should find nothing (transaction is fresh)
        state, timeout_outputs = state.check_timeouts()
        assert len(timeout_outputs) == 0

        # Now callback arrives
        cb = _make_callback()
        state, outputs = state.process_event(cb)
        assert len(outputs) == 1
        assert isinstance(outputs[0], MatchedPair)

    def test_timeout_detection(self) -> None:
        state = CallbackMatcherState()
        txn = _make_transaction()
        state, _ = state.process_event(txn)

        # Backdate the received_at to simulate timeout
        key = "M1:T100"
        state.pending_transactions[key].received_at = datetime.now(UTC) - timedelta(
            seconds=400
        )

        state, outputs = state.check_timeouts()
        assert len(outputs) == 1
        assert isinstance(outputs[0], AnomalyEvent)
        assert outputs[0].anomaly_type == "TIMEOUT"
        assert outputs[0].merchant_id == "M1"
        assert outputs[0].transaction_id == "T100"
        assert outputs[0].provider_id == "P1"
        assert key not in state.pending_transactions
        assert key not in get_active_keys()

    def test_timeout_includes_elapsed_seconds(self) -> None:
        state = CallbackMatcherState()
        txn = _make_transaction()
        state, _ = state.process_event(txn)

        state.pending_transactions["M1:T100"].received_at = datetime.now(
            UTC
        ) - timedelta(seconds=350)

        state, outputs = state.check_timeouts()
        assert outputs[0].details["elapsed_seconds"] >= 350

    def test_multiple_transactions_independent(self) -> None:
        state = CallbackMatcherState()
        txn1 = _make_transaction(merchant_id="M1", transaction_id="T1")
        txn2 = _make_transaction(merchant_id="M2", transaction_id="T2")
        state, _ = state.process_event(txn1)
        state, _ = state.process_event(txn2)

        assert len(state.pending_transactions) == 2

        # Callback for only one
        cb1 = _make_callback(merchant_id="M1", transaction_id="T1")
        state, outputs = state.process_event(cb1)

        assert len(outputs) == 1
        assert len(state.pending_transactions) == 1
        assert "M2:T2" in state.pending_transactions


class TestCallbackMatcherFunction:
    """Tests for the top-level callback_matcher function used by stateful_map."""

    def setup_method(self) -> None:
        clear_active_keys()

    def test_initializes_state_on_first_event(self) -> None:
        txn = _make_transaction()
        state, outputs = callback_matcher(None, txn)

        assert isinstance(state, CallbackMatcherState)
        assert len(outputs) == 0
        assert len(state.pending_transactions) == 1

    def test_tick_event_triggers_timeout_check(self) -> None:
        txn = _make_transaction()
        state, _ = callback_matcher(None, txn)

        # Backdate for timeout
        state.pending_transactions["M1:T100"].received_at = datetime.now(
            UTC
        ) - timedelta(seconds=400)

        state, outputs = callback_matcher(state, TickEvent(key="M1:T100"))
        assert len(outputs) == 1
        assert outputs[0].anomaly_type == "TIMEOUT"

    def test_unknown_event_type_ignored(self) -> None:
        state, outputs = callback_matcher(None, 12345)
        assert isinstance(state, CallbackMatcherState)
        assert len(outputs) == 0
