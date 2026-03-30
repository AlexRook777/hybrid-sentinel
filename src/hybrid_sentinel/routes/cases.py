"""API endpoints for agent investigation cases."""

from fastapi import APIRouter, HTTPException

from hybrid_sentinel.agent.store import get_case_by_id, get_recent_cases
from hybrid_sentinel.config import settings
from hybrid_sentinel.models import CaseReport

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/stats")
async def get_stats() -> dict:
    """Retrieve aggregate statistics about recent cases."""
    cases = get_recent_cases(limit=1000)
    cases_by_severity: dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }
    cases_by_pattern: dict[str, int] = {}
    for c in cases:
        cases_by_severity[c.severity] = (
            cases_by_severity.get(c.severity, 0) + 1
        )
        cases_by_pattern[c.pattern] = (
            cases_by_pattern.get(c.pattern, 0) + 1
        )
    return {
        "total_investigations": len(cases),
        "cases_by_severity": cases_by_severity,
        "cases_by_pattern": cases_by_pattern,
        "agent_enabled": settings.agent_enabled,
    }


@router.get("", response_model=list[CaseReport])
async def list_cases(limit: int = 50) -> list[CaseReport]:
    """Retrieve the most recent investigation case reports."""
    limit = min(max(1, limit), 200)
    return get_recent_cases(limit=limit)


@router.get("/{case_id}", response_model=CaseReport)
async def get_case(case_id: str) -> CaseReport:
    """Retrieve a specific investigation case report by ID.

    Note: Memory persistence is ephemeral. Old cases may not be found.
    """
    case = get_case_by_id(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
