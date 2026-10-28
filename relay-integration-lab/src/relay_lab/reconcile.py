"""Compare payment snapshots against a merchant-side ledger projection."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .models import LedgerEntry, Payment


class Discrepancy(StrEnum):
    MISSING_LEDGER = "missing_ledger_entry"
    ORPHAN_LEDGER = "orphan_ledger_entry"
    AMOUNT_MISMATCH = "amount_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"
    STATUS_MISMATCH = "status_mismatch"
    DUPLICATE_LEDGER = "duplicate_ledger_entry"


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    payment_id: str
    code: Discrepancy
    expected: str
    actual: str
    severity: str = "medium"


def reconcile(payments: Iterable[Payment], ledger: Iterable[LedgerEntry]) -> list[ReconciliationIssue]:
    payment_by_id = {p.id: p for p in payments}
    ledger_by_id: dict[str, list[LedgerEntry]] = {}
    for row in ledger:
        ledger_by_id.setdefault(row.payment_id, []).append(row)

    issues: list[ReconciliationIssue] = []
    for payment_id, payment in payment_by_id.items():
        rows = ledger_by_id.get(payment_id, [])
        if not rows:
            issues.append(ReconciliationIssue(payment_id, Discrepancy.MISSING_LEDGER, payment.status.value, "no ledger entry", "high"))
            continue
        if len(rows) > 1:
            issues.append(ReconciliationIssue(payment_id, Discrepancy.DUPLICATE_LEDGER, "1 entry", f"{len(rows)} entries", "high"))
        row = rows[0]
        if payment.amount != row.amount:
            issues.append(ReconciliationIssue(payment_id, Discrepancy.AMOUNT_MISMATCH, str(payment.amount), str(row.amount), "high"))
        if payment.currency.lower() != row.currency.lower():
            issues.append(ReconciliationIssue(payment_id, Discrepancy.CURRENCY_MISMATCH, payment.currency.upper(), row.currency.upper(), "high"))
        if payment.status != row.status:
            issues.append(ReconciliationIssue(payment_id, Discrepancy.STATUS_MISMATCH, payment.status.value, row.status.value))
    for payment_id in ledger_by_id.keys() - payment_by_id.keys():
        issues.append(ReconciliationIssue(payment_id, Discrepancy.ORPHAN_LEDGER, "known payment", "no matching payment", "high"))
    return issues
