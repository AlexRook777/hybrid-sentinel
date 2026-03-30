"""Data models for transaction events, callbacks, and anomalies."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class TransactionEvent(BaseModel):
    """Transaction initiation event from payment gateway."""

    type: Literal["transaction"] = "transaction"
    merchant_id: str = Field(..., min_length=1)
    transaction_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    provider_id: str = Field(..., min_length=1)
    timestamp: datetime


class CallbackEvent(BaseModel):
    """Callback event confirming transaction outcome."""

    type: Literal["callback"] = "callback"
    merchant_id: str = Field(..., min_length=1)
    transaction_id: str = Field(..., min_length=1)
    status: Literal["success", "failure", "pending"]
    actual_amount: Decimal = Field(..., gt=0)
    actual_currency: str = Field(..., min_length=3, max_length=3)
    provider_id: str = Field(..., min_length=1)
    timestamp: datetime


class AnomalyEvent(BaseModel):
    """Anomaly detected during stream processing."""

    type: Literal["anomaly"] = "anomaly"
    anomaly_type: str
    merchant_id: str
    transaction_id: str
    provider_id: str
    timestamp: datetime
    details: dict = Field(default_factory=dict)
    anomaly_score: float | None = None


class MatchedPair(BaseModel):
    """Successfully matched transaction-callback pair."""

    transaction: TransactionEvent
    callback: CallbackEvent
    match_timestamp: datetime


# Discriminated union for webhook endpoint
IncomingEvent = TransactionEvent | CallbackEvent
