"""Helpers for emitting Event rows in the same DB session as the underlying write."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session

from ..models import Event


def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def record_event(
    session: Session,
    *,
    group_id: UUID,
    kind: str,
    actor_id: UUID,
    subject_id: UUID | None = None,
    when: datetime,
    payload: dict | None = None,
) -> Event:
    event = Event(
        group_id=group_id,
        month=month_key(when),
        kind=kind,
        actor_id=actor_id,
        subject_id=subject_id,
        payload=payload or {},
    )
    session.add(event)
    return event
