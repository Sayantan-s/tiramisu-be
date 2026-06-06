from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from .config import get_settings


def issue_access_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("missing sub")
    try:
        return UUID(sub)
    except ValueError as exc:
        raise InvalidTokenError("invalid sub") from exc


class InvalidTokenError(Exception):
    pass
