from __future__ import annotations

import json

from .models import Payment, PaymentStatus
from .pipeline import WebhookPipeline
from .signatures import sign_payload


def run_demo() -> None:
    now = 1_800_000_000
    payment = Payment("pi_demo_01", 12900, "usd", PaymentStatus.PROCESSING, "cus_demo_01", "checkout-order-847")
    pipeline = WebhookPipeline("whsec_demo_only", [payment])
    event = {
        "id": "evt_demo_01",
        "type": "payment.succeeded",
        "created": now,
        "data": {"object": {"id": payment.id, "amount": payment.amount, "currency": payment.currency}},
    }
    raw = json.dumps(event, separators=(",", ":")).encode()
    result = pipeline.process(raw, sign_payload(raw, pipeline.secret, now), now=now)
    print("Payment webhook simulation")
    print(json.dumps(result, indent=2))
    print(f"Ledger entries: {len(pipeline.ledger)}")
    print(f"Audit decisions: {len(pipeline.audit)}")


if __name__ == "__main__":
    run_demo()
