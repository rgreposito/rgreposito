"""Explicit payment lifecycle transitions; invalid transitions fail closed."""

from .models import PaymentStatus


class InvalidTransition(ValueError):
    pass


_ALLOWED: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.REQUIRES_PAYMENT_METHOD: {PaymentStatus.REQUIRES_ACTION, PaymentStatus.PROCESSING, PaymentStatus.FAILED, PaymentStatus.CANCELED},
    PaymentStatus.REQUIRES_ACTION: {PaymentStatus.PROCESSING, PaymentStatus.FAILED, PaymentStatus.CANCELED},
    PaymentStatus.PROCESSING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.CANCELED},
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.CANCELED: set(),
    PaymentStatus.REFUNDED: set(),
}


def transition(current: PaymentStatus, target: PaymentStatus) -> PaymentStatus:
    if current == target:
        return current
    if target not in _ALLOWED[current]:
        raise InvalidTransition(f"payment cannot transition from {current.value} to {target.value}")
    return target
