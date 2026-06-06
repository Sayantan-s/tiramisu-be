from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..deps import CurrentUserDep, SessionDep
from .auth import UserOut

router = APIRouter(prefix="/me", tags=["me"])


class UpdateMeIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    avatar: str | None = None


@router.get("", response_model=UserOut)
def read_me(user: CurrentUserDep) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)


@router.patch("", response_model=UserOut)
def update_me(payload: UpdateMeIn, user: CurrentUserDep, session: SessionDep) -> UserOut:
    if payload.name is not None:
        user.name = payload.name
    if payload.avatar is not None:
        user.avatar = payload.avatar
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)
