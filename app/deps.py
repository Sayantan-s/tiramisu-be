from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from .db import get_session
from .models import User
from .security import InvalidTokenError, decode_access_token

SessionDep = Annotated[Session, Depends(get_session)]


def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


CurrentUserDep = Annotated[User, Depends(current_user)]
