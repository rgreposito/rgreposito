# Architecture and trade-offs

The reference path is: raw webhook bytes → signature and timestamp checks → schema validation → event-ID dedupe → explicit payment transition → ledger projection → reconciliation/audit.

## Separate two forms of dedupe

An inbound webhook's event ID protects a receiver from retrying the same event. An outgoing API request's idempotency key protects a client retrying the same logical operation after an ambiguous timeout. They have different namespaces, payload fingerprints and retention requirements; one cannot replace the other.

## Why fail closed on state transitions?

A late `processing` event must not revert a payment that is already `succeeded`. The sample transition matrix rejects impossible regressions and records a quarantine outcome. Some valid provider flows are more nuanced; in a production adapter, use the provider's SDK and retrieve authoritative state when event order is ambiguous.

## What production changes

- Replace in-memory event IDs and locks with durable unique constraints and atomic reservations.
- Persist payment state, ledger projection and outbox intent within one database transaction.
- Deliver downstream side effects from a durable outbox to idempotent consumers.
- Scope credentials and keys per tenant/environment; use managed secret storage and rotation.
- Add bounded retry with jitter, dead-letter handling, tracing, redaction, and SLO burn-rate alerts.
- Make reconciliation a continuous operational workflow with explicit ownership and approval for financial repair.
