"""Raw-body HMAC verification helpers for the reference integration."""

from __future__ import annotations

import hashlib
import hmac
import time


class SignatureError(ValueError):
    """Signature missing, malformed, stale, or invalid."""


def sign_payload(payload: bytes, secret: str, timestamp: int) -> str:
    signed = str(timestamp).encode("ascii") + b"." + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    *,
    now: int | None = None,
    tolerance_seconds: int = 300,
) -> int:
    """Verify the exact raw bytes and timestamp; return signed timestamp."""
    if not secret:
        raise SignatureError("signing secret is not configured")
    try:
        fields: dict[str, list[str]] = {}
        for part in signature_header.split(","):
            key, value = part.strip().split("=", 1)
            if key and value:
                fields.setdefault(key, []).append(value)
        timestamp = int(fields["t"][0])
        candidates = fields["v1"]
    except (ValueError, KeyError, IndexError) as exc:
        raise SignatureError("malformed signature header") from exc

    if tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be non-negative")
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > tolerance_seconds:
        raise SignatureError("signature timestamp outside tolerance")

    expected = sign_payload(payload, secret, timestamp).split("v1=", 1)[1]
    if not any(hmac.compare_digest(expected, candidate) for candidate in candidates):
        raise SignatureError("signature digest does not match payload")
    return timestamp
