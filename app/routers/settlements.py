from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import CurrentUserDep, SessionDep
from ..models import Settlement
from ..services.events import record_event
from .groups import _ensure_member

router = APIRouter(prefix="/groups/{group_id}/settlements", tags=["settlements"])


class SettlementIn(BaseModel):
    from_id: UUID
    to_id: UUID
    amount: int = Field(gt=0)
    paid_at: datetime
    note: str | None = None


class SettlementOut(BaseModel):
    id: UUID
    group_id: UUID
    from_id: UUID
    to_id: UUID
    amount: int
    paid_at: datetime
    note: str | None
    created_by: UUID
    created_at: datetime


def _to_out(s: Settlement) -> SettlementOut:
    return SettlementOut(
        id=s.id,
        group_id=s.group_id,
        from_id=s.from_id,
        to_id=s.to_id,
        amount=s.amount,
        paid_at=s.paid_at,
        note=s.note,
        created_by=s.created_by,
        created_at=s.created_at,
    )


@router.get("", response_model=list[SettlementOut])
def list_settlements(
    group_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
    since: datetime | None = Query(default=None),
) -> list[SettlementOut]:
    _ensure_member(session, group_id, user.id)
    stmt = (
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .where(Settlement.deleted_at.is_(None))
    )
    if since is not None:
        stmt = stmt.where(Settlement.created_at >= since)
    stmt = stmt.order_by(Settlement.paid_at.desc())
    return [_to_out(s) for s in session.exec(stmt).all()]


@router.post("", response_model=SettlementOut, status_code=201)
def create_settlement(
    group_id: UUID,
    payload: SettlementIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> SettlementOut:
    _ensure_member(session, group_id, user.id)
    if payload.from_id == payload.to_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "from and to must differ")
    settlement = Settlement(
        group_id=group_id,
        from_id=payload.from_id,
        to_id=payload.to_id,
        amount=payload.amount,
        paid_at=payload.paid_at,
        note=payload.note,
        created_by=user.id,
    )
    session.add(settlement)
    session.flush()
    record_event(
        session,
        group_id=group_id,
        kind="settlement_recorded",
        actor_id=user.id,
        subject_id=settlement.id,
        when=settlement.paid_at,
        payload={"from": str(payload.from_id), "to": str(payload.to_id), "amount": payload.amount},
    )
    session.commit()
    session.refresh(settlement)
    return _to_out(settlement)


@router.delete("/{settlement_id}", status_code=204)
def delete_settlement(
    group_id: UUID,
    settlement_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    _ensure_member(session, group_id, user.id)
    settlement = session.get(Settlement, settlement_id)
    if (
        settlement is None
        or settlement.group_id != group_id
        or settlement.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Settlement not found")
    now = datetime.now(timezone.utc)
    settlement.deleted_at = now
    session.add(settlement)
    record_event(
        session,
        group_id=group_id,
        kind="settlement_deleted",
        actor_id=user.id,
        subject_id=settlement.id,
        when=now,
    )
    session.commit()
