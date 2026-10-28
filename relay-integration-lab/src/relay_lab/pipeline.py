"""Webhook-to-payment-state pipeline with explicit outcomes and audit records."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from .lifecycle import InvalidTransition, transition
from .models import AuditEvent, LedgerEntry, Payment, PaymentStatus
from .signatures import SignatureError, verify_signature

_EVENT_TARGETS = {
    "payment.requires_action": PaymentStatus.REQUIRES_ACTION,
    "payment.processing": PaymentStatus.PROCESSING,
    "payment.succeeded": PaymentStatus.SUCCEEDED,
    "payment.failed": PaymentStatus.FAILED,
    "payment.canceled": PaymentStatus.CANCELED,
    "payment.refunded": PaymentStatus.REFUNDED,
}


class WebhookPipeline:
    """In-memory reference only: persist event IDs and state for real services."""

    def __init__(self, secret: str, payments: list[Payment] | None = None, *, tolerance_seconds: int = 300):
        self.secret = secret
        self.payments = {p.id: p for p in payments or []}
        self.tolerance_seconds = tolerance_seconds
        self.seen_event_ids: set[str] = set()
        self.ledger: list[LedgerEntry] = []
        self.audit: list[AuditEvent] = []
        self._lock = threading.RLock()

    def _audit(self, event_type: str, subject: str, outcome: str, reason: str, now: int, **details: Any) -> None:
        self.audit.append(AuditEvent(event_type, subject, outcome, reason, now, details))

    def process(self, raw_payload: bytes, signature_header: str, *, now: int | None = None) -> dict[str, Any]:
        current = int(time.time()) if now is None else now
        try:
            signed_at = verify_signature(raw_payload, signature_header, self.secret, now=current, tolerance_seconds=self.tolerance_seconds)
        except SignatureError as exc:
            with self._lock:
                self._audit("webhook.received", "unknown", "rejected", str(exc), current)
            return {"outcome": "rejected", "reason": str(exc)}

        try:
            body = json.loads(raw_payload)
            event_id, event_type = body["id"], body["type"]
            obj = body["data"]["object"]
            payment_id = obj["id"]
            amount = int(obj["amount"])
            currency = str(obj["currency"]).lower()
            if not all(isinstance(v, str) and v for v in (event_id, event_type, payment_id, currency)) or amount < 0:
                raise ValueError("invalid required field")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            with self._lock:
                self._audit("webhook.received", "unknown", "rejected", "payload schema invalid", current)
            return {"outcome": "rejected", "reason": "payload schema invalid"}

        with self._lock:
            if event_id in self.seen_event_ids:
                self._audit(event_type, event_id, "duplicate", "event ID already processed", current, signed_at=signed_at)
                return {"outcome": "duplicate", "event_id": event_id}
            self.seen_event_ids.add(event_id)
            payment = self.payments.get(payment_id)
            target = _EVENT_TARGETS.get(event_type)
            if payment is None:
                self._audit(event_type, event_id, "quarantined", "payment not found", current, payment_id=payment_id)
                return {"outcome": "quarantined", "event_id": event_id, "reason": "payment not found"}
            if target is None:
                self._audit(event_type, event_id, "ignored", "unsupported event type", current, payment_id=payment_id)
                return {"outcome": "ignored", "event_id": event_id, "reason": "unsupported event type"}
            if amount != payment.amount or currency != payment.currency.lower():
                self._audit(event_type, event_id, "quarantined", "amount or currency mismatch", current, payment_id=payment_id)
                return {"outcome": "quarantined", "event_id": event_id, "reason": "payment attributes mismatch"}
            try:
                next_status = transition(payment.status, target)
            except InvalidTransition as exc:
                self._audit(event_type, event_id, "quarantined", str(exc), current, payment_id=payment_id)
                return {"outcome": "quarantined", "event_id": event_id, "reason": str(exc)}

            payment.status = next_status
            if next_status in {PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED}:
                self.ledger.append(LedgerEntry(payment.id, payment.amount, payment.currency.lower(), next_status, event_id))
            self._audit(event_type, event_id, "applied", "signature and transition validated", current, payment_id=payment_id, status=next_status.value)
            return {"outcome": "applied", "event_id": event_id, "payment_id": payment_id, "status": next_status.value}
