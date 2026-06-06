from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import CurrentUserDep, SessionDep
from ..models import Group, GroupMember, User

router = APIRouter(prefix="/groups", tags=["groups"])


class CreateGroupIn(BaseModel):
    kind: Literal["roomies", "trips"]
    name: str = Field(min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=8)


class MemberOut(BaseModel):
    id: UUID
    name: str
    avatar: str | None
    role: Literal["owner", "member"]
    joined_at: datetime


class GroupOut(BaseModel):
    id: UUID
    kind: Literal["roomies", "trips"]
    name: str
    icon: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    members: list[MemberOut]


def _serialize_group(group: Group, session) -> GroupOut:
    rows = session.exec(
        select(GroupMember, User)
        .where(GroupMember.group_id == group.id)
        .where(GroupMember.user_id == User.id)
    ).all()
    members = [
        MemberOut(
            id=user.id,
            name=user.name,
            avatar=user.avatar,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, user in rows
    ]
    return GroupOut(
        id=group.id,
        kind=group.kind,
        name=group.name,
        icon=group.icon,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members,
    )


def _ensure_member(session, group_id: UUID, user_id: UUID) -> GroupMember:
    member = session.exec(
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .where(GroupMember.user_id == user_id)
    ).first()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    return member


@router.get("", response_model=list[GroupOut])
def list_my_groups(user: CurrentUserDep, session: SessionDep) -> list[GroupOut]:
    rows = session.exec(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id)
        .order_by(Group.updated_at.desc())
    ).all()
    return [_serialize_group(g, session) for g in rows]


@router.post("", response_model=GroupOut, status_code=201)
def create_group(payload: CreateGroupIn, user: CurrentUserDep, session: SessionDep) -> GroupOut:
    group = Group(kind=payload.kind, name=payload.name, icon=payload.icon, created_by=user.id)
    session.add(group)
    session.flush()
    session.add(GroupMember(group_id=group.id, user_id=user.id, role="owner"))
    session.commit()
    session.refresh(group)
    return _serialize_group(group, session)


@router.get("/{group_id}", response_model=GroupOut)
def read_group(group_id: UUID, user: CurrentUserDep, session: SessionDep) -> GroupOut:
    _ensure_member(session, group_id, user.id)
    group = session.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    return _serialize_group(group, session)


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: UUID, user: CurrentUserDep, session: SessionDep) -> None:
    member = _ensure_member(session, group_id, user.id)
    if member.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can delete the group")
    group = session.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    # Cascade: delete members rows, then group. (Expenses/Settlements/Events come in Phase 3.)
    for m in session.exec(select(GroupMember).where(GroupMember.group_id == group_id)).all():
        session.delete(m)
    session.delete(group)
    session.commit()


@router.post("/{group_id}/leave", status_code=204)
def leave_group(group_id: UUID, user: CurrentUserDep, session: SessionDep) -> None:
    member = _ensure_member(session, group_id, user.id)
    session.delete(member)

    remaining = session.exec(
        select(GroupMember).where(GroupMember.group_id == group_id)
    ).all()
    if not remaining:
        group = session.get(Group, group_id)
        if group is not None:
            session.delete(group)
    elif member.role == "owner" and not any(r.role == "owner" for r in remaining):
        oldest = sorted(remaining, key=lambda r: r.joined_at)[0]
        oldest.role = "owner"
        session.add(oldest)

    if remaining_group := session.get(Group, group_id):
        remaining_group.updated_at = datetime.now(timezone.utc)
        session.add(remaining_group)
    session.commit()
