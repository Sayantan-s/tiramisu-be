"""Dev-only endpoints. Gated by `Settings.dev_mode`.

When dev_mode is off, every handler returns 404 so the surface area is invisible
in production.

`POST /dev/seed-roommate` creates a user with a generated phone, drops them into
a group you're already in, and returns an access token for that user so the
client can "act as" them.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..config import get_settings
from ..deps import CurrentUserDep, SessionDep
from ..models import GroupMember, User
from ..security import issue_access_token
from ..services.events import record_event
from .groups import _ensure_member

router = APIRouter(prefix="/dev", tags=["dev"])


def _guard() -> None:
    if not get_settings().dev_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


class SeedRoommateIn(BaseModel):
    group_id: UUID
    name: str = Field(min_length=1, max_length=80)
    avatar: str | None = None
    role: Literal["owner", "member"] = "member"


class SeededUserOut(BaseModel):
    id: UUID
    phone: str
    name: str
    avatar: str | None
    created_at: datetime


class SeedRoommateOut(BaseModel):
    user: SeededUserOut
    access_token: str


@router.post("/seed-roommate", response_model=SeedRoommateOut, status_code=201)
def seed_roommate(
    payload: SeedRoommateIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> SeedRoommateOut:
    _guard()
    _ensure_member(session, payload.group_id, user.id)

    dummy = User(
        phone=f"dev_{secrets.token_urlsafe(8)}",
        name=payload.name,
        avatar=payload.avatar,
    )
    session.add(dummy)
    session.flush()

    session.add(GroupMember(group_id=payload.group_id, user_id=dummy.id, role=payload.role))
    record_event(
        session,
        group_id=payload.group_id,
        kind="member_joined",
        actor_id=dummy.id,
        subject_id=dummy.id,
        when=datetime.utcnow(),
        payload={"name": dummy.name, "via": "dev"},
    )
    session.commit()
    session.refresh(dummy)

    token = issue_access_token(dummy.id)
    return SeedRoommateOut(
        user=SeededUserOut(
            id=dummy.id,
            phone=dummy.phone,
            name=dummy.name,
            avatar=dummy.avatar,
            created_at=dummy.created_at,
        ),
        access_token=token,
    )
