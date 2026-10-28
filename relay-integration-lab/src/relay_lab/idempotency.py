"""Thread-safe in-memory idempotency reference."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class IdempotencyConflict(ValueError):
    """A key was reused with a different request payload."""


@dataclass(frozen=True, slots=True)
class _Record(Generic[T]):
    fingerprint: str
    result: T


def _fingerprint(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore(Generic[T]):
    """Same key + same payload returns the cached result; changed payload conflicts.

    The lock covers operation execution, proving the single-process concurrency
    invariant. Multi-worker services need a durable atomic reservation.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, _Record[T]] = {}

    def execute(self, key: str, payload: object, operation: Callable[[], T]) -> tuple[T, bool]:
        if not key or len(key) > 255:
            raise ValueError("idempotency key must contain 1..255 characters")
        fingerprint = _fingerprint(payload)
        with self._lock:
            previous = self._records.get(key)
            if previous:
                if previous.fingerprint != fingerprint:
                    raise IdempotencyConflict("key was already used with a different request")
                return previous.result, True
            result = operation()
            self._records[key] = _Record(fingerprint=fingerprint, result=result)
            return result, False
