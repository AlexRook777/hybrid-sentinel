"""In-memory store for recent investigation cases."""

import threading
from collections import deque

from hybrid_sentinel.models import CaseReport

_cases: deque[CaseReport] = deque(maxlen=1000)
_cases_by_id: dict[str, CaseReport] = {}
_cases_lock = threading.Lock()


def add_case(case: CaseReport) -> None:
    """Add a case report to the in-memory store."""
    with _cases_lock:
        # If deque is at capacity, the oldest item is evicted
        if len(_cases) == _cases.maxlen:
            evicted = _cases[-1]
            _cases_by_id.pop(evicted.case_id, None)
        _cases.appendleft(case)
        _cases_by_id[case.case_id] = case


def get_recent_cases(limit: int = 50) -> list[CaseReport]:
    """Retrieve the most recent case reports."""
    with _cases_lock:
        return list(_cases)[:limit]


def get_case_by_id(case_id: str) -> CaseReport | None:
    """Retrieve a specific case report by ID (O(1) lookup)."""
    with _cases_lock:
        return _cases_by_id.get(case_id)


def clear_cases() -> None:
    """Clear all cases (useful for testing)."""
    with _cases_lock:
        _cases.clear()
        _cases_by_id.clear()
