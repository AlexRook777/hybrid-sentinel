"""Anomaly detection routes."""

from fastapi import APIRouter, HTTPException

from hybrid_sentinel.anomaly import get_scorer

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("/stats")
async def get_anomaly_stats() -> dict:
    """Get anomaly scorer statistics.

    Returns:
        Dictionary with warmup status, events processed, anomalies emitted, etc.
    """
    scorer = get_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="Anomaly scorer not running")

    return scorer.get_stats()
