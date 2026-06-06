from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import CurrentUserDep, SessionDep
from ..lib.invite_code import generate_invite_code
from ..models import Group, GroupMember, Invite
from .groups import GroupOut, _ensure_member, _serialize_group

router = APIRouter(tags=["invites"])


class CreateInviteIn(BaseModel):
    expires_in_hours: int = Field(default=24 * 7, ge=1, le=24 * 30)
    max_uses: int = Field(default=5, ge=1, le=50)


class InviteOut(BaseModel):
    code: str
    group_id: UUID
    expires_at: datetime
    max_uses: int
    used_count: int


@router.post("/groups/{group_id}/invites", response_model=InviteOut, status_code=201)
def create_invite(
    group_id: UUID,
    payload: CreateInviteIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> InviteOut:
    _ensure_member(session, group_id, user.id)

    for _ in range(5):
        code = generate_invite_code()
        if session.get(Invite, code) is None:
            break
    else:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not allocate invite code")

    invite = Invite(
        code=code,
        group_id=group_id,
        created_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours),
        max_uses=payload.max_uses,
    )
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return InviteOut(
        code=invite.code,
        group_id=invite.group_id,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        used_count=invite.used_count,
    )


@router.post("/invites/{code}/accept", response_model=GroupOut)
def accept_invite(code: str, user: CurrentUserDep, session: SessionDep) -> GroupOut:
    invite = session.get(Invite, code.upper())
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")

    now = datetime.now(timezone.utc)
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status.HTTP_410_GONE, "Invite expired")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status.HTTP_410_GONE, "Invite used up")

    existing = session.exec(
        select(GroupMember)
        .where(GroupMember.group_id == invite.group_id)
        .where(GroupMember.user_id == user.id)
    ).first()
    if existing is None:
        session.add(GroupMember(group_id=invite.group_id, user_id=user.id, role="member"))
        invite.used_count += 1
        session.add(invite)

    group = session.get(Group, invite.group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group no longer exists")
    group.updated_at = now
    session.add(group)
    session.commit()
    session.refresh(group)
    return _serialize_group(group, session)
