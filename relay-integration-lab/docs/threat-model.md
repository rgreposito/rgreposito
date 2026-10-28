# Threat model

## Assets

Payment-state consistency, merchant order fulfillment, ledger integrity, webhook signing secrets, tenant isolation, and traceable decision rationale.

## Threats and reference controls

| Threat | Control | Remaining limitation |
| --- | --- | --- |
| Forged webhook | HMAC over raw body plus timestamp tolerance | Use the provider's maintained SDK in production |
| Replay of old signed request | Timestamp tolerance | Durable event dedupe and clock synchronization still required |
| Duplicate delivery | Event-ID dedupe | In-memory only; not multi-replica safe |
| Same idempotency key, changed payload | Request fingerprint conflict | Durable key retention/reservation policy not implemented |
| Out-of-order lifecycle event | Explicit transition allow-list | Some cases need authoritative provider retrieval |
| Amount/currency mismatch | Quarantine before mutation | Production needs a reviewed remediation path |
| Ledger drift | Reconciliation discrepancy report | No automatic repair, by design |

This is not a security certification, payment processor, PCI assessment, or official Stripe integration. It stores no card data or credentials.
