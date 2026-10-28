import json
import threading
import unittest

from relay_lab.idempotency import IdempotencyConflict, IdempotencyStore
from relay_lab.lifecycle import InvalidTransition, transition
from relay_lab.models import LedgerEntry, Payment, PaymentStatus
from relay_lab.pipeline import WebhookPipeline
from relay_lab.reconcile import Discrepancy, reconcile
from relay_lab.signatures import SignatureError, sign_payload, verify_signature


class SignatureTests(unittest.TestCase):
    def test_valid_and_tampered_payloads(self):
        body = b'{"id":"evt_1"}'
        header = sign_payload(body, "secret", 1000)
        self.assertEqual(verify_signature(body, header, "secret", now=1000), 1000)
        with self.assertRaisesRegex(SignatureError, "digest"):
            verify_signature(body + b" ", header, "secret", now=1000)

    def test_stale_signature_is_rejected(self):
        body = b"body"
        with self.assertRaisesRegex(SignatureError, "outside tolerance"):
            verify_signature(body, sign_payload(body, "secret", 1000), "secret", now=1200, tolerance_seconds=100)


class IdempotencyTests(unittest.TestCase):
    def test_duplicate_returns_cached_result_and_changed_payload_conflicts(self):
        store = IdempotencyStore[str]()
        calls = []
        operation = lambda: calls.append(1) or "charge_1"
        first, duplicate1 = store.execute("order-1", {"amount": 500}, operation)
        second, duplicate2 = store.execute("order-1", {"amount": 500}, operation)
        self.assertEqual((first, second), ("charge_1", "charge_1"))
        self.assertFalse(duplicate1)
        self.assertTrue(duplicate2)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(IdempotencyConflict):
            store.execute("order-1", {"amount": 700}, operation)

    def test_concurrent_requests_execute_once(self):
        store = IdempotencyStore[int]()
        calls, results = [], []
        barrier = threading.Barrier(6)
        def worker():
            barrier.wait()
            results.append(store.execute("same-key", {"amount": 100}, lambda: calls.append(1) or 9)[0])
        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(results, [9] * 6)


class LifecycleAndReconciliationTests(unittest.TestCase):
    def test_terminal_state_cannot_regress(self):
        with self.assertRaises(InvalidTransition):
            transition(PaymentStatus.SUCCEEDED, PaymentStatus.PROCESSING)

    def test_reconciliation_reports_missing_and_mismatched_rows(self):
        payment = Payment("pi_1", 2500, "usd", PaymentStatus.SUCCEEDED, "cus_1", "order-1")
        rows = [LedgerEntry("pi_1", 2400, "eur", PaymentStatus.PROCESSING, "evt_1")]
        codes = {i.code for i in reconcile([payment], rows)}
        self.assertEqual(codes, {Discrepancy.AMOUNT_MISMATCH, Discrepancy.CURRENCY_MISMATCH, Discrepancy.STATUS_MISMATCH})


class PipelineTests(unittest.TestCase):
    def test_signed_event_applies_once(self):
        now = 1800000000
        payment = Payment("pi_1", 1200, "usd", PaymentStatus.PROCESSING, "cus_1", "order-1")
        pipeline = WebhookPipeline("test_secret", [payment])
        event = {"id": "evt_1", "type": "payment.succeeded", "data": {"object": {"id": "pi_1", "amount": 1200, "currency": "usd"}}}
        body = json.dumps(event, separators=(",", ":")).encode()
        signature = sign_payload(body, "test_secret", now)
        self.assertEqual(pipeline.process(body, signature, now=now)["outcome"], "applied")
        self.assertEqual(pipeline.process(body, signature, now=now)["outcome"], "duplicate")
        self.assertEqual(len(pipeline.ledger), 1)


if __name__ == "__main__":
    unittest.main()
