# Relay Integration Lab

**An independent forward-deployed payment integration engineering lab.**

Relay explores the failure modes between a payment provider and an enterprise merchant's real systems: signed webhooks, duplicate delivery, idempotent API requests, payment state transitions, and ledger reconciliation.

> Independent portfolio reference—not an official Stripe product. It uses synthetic data, no Stripe credentials, and makes no live payment calls.

## Run the executable reference

Python 3.11+, no runtime dependencies:

```bash
PYTHONPATH=src python -m relay_lab
PYTHONPATH=src python -m unittest discover -s tests -v
```

The demo signs a synthetic success event, validates it against the exact raw body, advances a payment through an explicit state machine, and records the resulting ledger projection and audit outcome.

## Try the workbench

Open [`web/index.html`](web/index.html) in a browser. The workbench lets you inspect synthetic payments, simulate webhook retries, inspect reconciliation issues, and run pre-launch integration diagnostics.

## Design focus

- Verify webhook HMAC and timestamp before parsing the payload.
- Keep inbound event deduplication distinct from outbound request idempotency.
- Reject reuse of an idempotency key when the request fingerprint changes.
- Make concurrency behavior testable; duplicate requests must not perform the operation twice in one process.
- Quarantine impossible payment transitions and amount/currency mismatches.
- Reconcile missing, orphaned, duplicate, or inconsistent ledger rows without silently repairing financial state.

See [architecture](docs/architecture.md), [runbook](docs/runbook.md), and [threat model](docs/threat-model.md) for trade-offs and operational handling.

## Production boundary

The locks, event-ID set, and ledger are in-memory and single-process. A production implementation needs durable unique constraints, transaction/outbox semantics, provider SDK verification, tenant-scoped credentials, bounded retries, observability, and a reviewed repair workflow. This project makes no claims of production use, measured latency, certification, or employer affiliation.
