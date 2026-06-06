"""OTP issuance + verification.

Dev mode (`Settings.dev_mode=True`): the OTP is always `Settings.dev_otp` (default
`"123456"`). No real SMS is sent. Verification accepts any phone with that code.

In production this module is the only place that needs to learn about a real SMS
gateway. The interface is intentionally minimal: a request creates a pending row,
verify checks code + request_id, marks it consumed.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..config import get_settings


@dataclass
class OtpChallenge:
    request_id: str
    phone: str
    code: str
    expires_at: datetime
    consumed: bool = False


_store: dict[str, OtpChallenge] = {}


def request_otp(phone: str) -> OtpChallenge:
    settings = get_settings()
    code = settings.dev_otp if settings.dev_mode else f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        request_id=secrets.token_urlsafe(16),
        phone=phone,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    _store[challenge.request_id] = challenge
    # Real-SMS path would go here.
    return challenge


def verify_otp(phone: str, code: str) -> bool:
    """Returns True if any unexpired, unconsumed challenge for `phone` matches `code`.

    Consumes the matching challenge so the same code can't be replayed.
    """
    now = datetime.now(timezone.utc)
    for challenge in list(_store.values()):
        if (
            challenge.phone == phone
            and not challenge.consumed
            and challenge.expires_at > now
            and challenge.code == code
        ):
            challenge.consumed = True
            return True
    return False


def reset_for_tests() -> None:
    _store.clear()
