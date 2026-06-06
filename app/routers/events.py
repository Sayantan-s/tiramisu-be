from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import CurrentUserDep, SessionDep
from ..models import Event
from ..services.events import record_event
from .groups import _ensure_member

router = APIRouter(prefix="/groups/{group_id}/events", tags=["events"])


class EventOut(BaseModel):
    id: UUID
    group_id: UUID
    month: str
    kind: str
    actor_id: UUID
    subject_id: UUID | None
    payload: dict
    created_at: datetime


class CommentIn(BaseModel):
    kind: Literal["comment"]
    subject_id: UUID
    payload: dict = Field(default_factory=dict)  # expect {body: "..."}


@router.get("", response_model=list[EventOut])
def list_events(
    group_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    since: datetime | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[EventOut]:
    _ensure_member(session, group_id, user.id)
    stmt = select(Event).where(Event.group_id == group_id)
    if month is not None:
        stmt = stmt.where(Event.month == month)
    if since is not None:
        stmt = stmt.where(Event.created_at >= since)
    stmt = stmt.order_by(Event.created_at.asc()).limit(limit)
    rows = session.exec(stmt).all()
    return [
        EventOut(
            id=e.id,
            group_id=e.group_id,
            month=e.month,
            kind=e.kind,
            actor_id=e.actor_id,
            subject_id=e.subject_id,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in rows
    ]


@router.post("", response_model=EventOut, status_code=201)
def create_comment(
    group_id: UUID,
    payload: CommentIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> EventOut:
    _ensure_member(session, group_id, user.id)
    body = (payload.payload or {}).get("body", "")
    if not isinstance(body, str) or not body.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Comment body required")
    now = datetime.now(timezone.utc)
    event = record_event(
        session,
        group_id=group_id,
        kind="comment",
        actor_id=user.id,
        subject_id=payload.subject_id,
        when=now,
        payload={"body": body.strip()},
    )
    session.commit()
    session.refresh(event)
    return EventOut(
        id=event.id,
        group_id=event.group_id,
        month=event.month,
        kind=event.kind,
        actor_id=event.actor_id,
        subject_id=event.subject_id,
        payload=event.payload,
        created_at=event.created_at,
    )
