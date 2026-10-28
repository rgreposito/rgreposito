from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PaymentStatus(StrEnum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


@dataclass(slots=True)
class Payment:
    id: str
    amount: int
    currency: str
    status: PaymentStatus
    customer_id: str
    idempotency_key: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    payment_id: str
    amount: int
    currency: str
    status: PaymentStatus
    source_reference: str


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    subject: str
    outcome: str
    reason: str
    recorded_at: int
    details: dict[str, Any] = field(default_factory=dict)
