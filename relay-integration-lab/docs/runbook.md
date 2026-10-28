# Payment integration runbook

## Webhook signature failures
1. Confirm the endpoint secret maps to the correct sandbox or live environment.
2. Verify the exact raw request bytes; do not parse and re-serialize JSON before verification.
3. Check server clock drift and the timestamp tolerance.
4. Keep secrets and sensitive payload fields out of logs. Correlate with event and request IDs.

## Order and payment states disagree
1. Locate the payment ID and event IDs in the provider view, webhook receiver, order service, and finance ledger.
2. Compare amount in integer minor units, currency, status and source reference.
3. Inspect duplicate and out-of-order deliveries before replaying.
4. Run reconciliation and preserve evidence rather than editing ledger rows ad hoc.
5. Use a reviewed correction path with stable idempotency and an auditable operator decision.

## Retry discipline
- Retry transient network failures and documented rate limits with bounded exponential backoff and jitter.
- Do not blindly retry permanent validation errors.
- Reuse an idempotency key for the same logical request; changed payloads need a new request/key.
- Treat timeout-after-commit as ambiguous and reconcile before sending a new logical operation.
- Acknowledge valid webhooks quickly and push slow downstream work to a durable queue/outbox.
