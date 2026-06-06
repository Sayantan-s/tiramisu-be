from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import CurrentUserDep, SessionDep
from ..lib.split import validate_split
from ..models import Expense
from ..services.events import record_event
from .groups import _ensure_member

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])


class RecurringIn(BaseModel):
    cadence: Literal["monthly"]
    nextDueIso: str


class ExpenseIn(BaseModel):
    amount: int = Field(gt=0)
    currency: Literal["INR"] = "INR"
    payer_id: UUID
    paid_at: datetime
    category: str
    description: str | None = None
    receipt_uri: str | None = None
    source: Literal["manual", "receipt", "sms"] = "manual"
    split: dict
    recurring: RecurringIn | None = None


class ExpenseOut(BaseModel):
    id: UUID
    group_id: UUID
    amount: int
    currency: str
    payer_id: UUID
    paid_at: datetime
    category: str
    description: str | None
    receipt_uri: str | None
    source: str
    split: dict
    recurring: dict | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


def _to_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id,
        group_id=e.group_id,
        amount=e.amount,
        currency=e.currency,
        payer_id=e.payer_id,
        paid_at=e.paid_at,
        category=e.category,
        description=e.description,
        receipt_uri=e.receipt_uri,
        source=e.source,
        split=e.split,
        recurring=e.recurring,
        created_by=e.created_by,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    group_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
    since: datetime | None = Query(default=None),
) -> list[ExpenseOut]:
    _ensure_member(session, group_id, user.id)
    stmt = select(Expense).where(Expense.group_id == group_id).where(Expense.deleted_at.is_(None))
    if since is not None:
        stmt = stmt.where(Expense.updated_at >= since)
    stmt = stmt.order_by(Expense.paid_at.desc())
    return [_to_out(e) for e in session.exec(stmt).all()]


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(
    group_id: UUID,
    payload: ExpenseIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> ExpenseOut:
    _ensure_member(session, group_id, user.id)

    ok, reason = validate_split(payload.amount, payload.split)
    if not ok:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)

    expense = Expense(
        group_id=group_id,
        amount=payload.amount,
        currency=payload.currency,
        payer_id=payload.payer_id,
        paid_at=payload.paid_at,
        category=payload.category,
        description=payload.description,
        receipt_uri=payload.receipt_uri,
        source=payload.source,
        split=payload.split,
        recurring=payload.recurring.model_dump() if payload.recurring else None,
        created_by=user.id,
    )
    session.add(expense)
    session.flush()
    record_event(
        session,
        group_id=group_id,
        kind="expense_added",
        actor_id=user.id,
        subject_id=expense.id,
        when=expense.paid_at,
        payload={"amount": expense.amount, "category": expense.category},
    )
    session.commit()
    session.refresh(expense)
    return _to_out(expense)


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    group_id: UUID,
    expense_id: UUID,
    payload: ExpenseIn,
    user: CurrentUserDep,
    session: SessionDep,
) -> ExpenseOut:
    _ensure_member(session, group_id, user.id)
    expense = session.get(Expense, expense_id)
    if expense is None or expense.group_id != group_id or expense.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")

    ok, reason = validate_split(payload.amount, payload.split)
    if not ok:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "recurring":
            expense.recurring = payload.recurring.model_dump() if payload.recurring else None
        else:
            setattr(expense, field, value)
    expense.updated_at = datetime.now(timezone.utc)
    session.add(expense)
    record_event(
        session,
        group_id=group_id,
        kind="expense_updated",
        actor_id=user.id,
        subject_id=expense.id,
        when=expense.updated_at,
    )
    session.commit()
    session.refresh(expense)
    return _to_out(expense)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    group_id: UUID,
    expense_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    _ensure_member(session, group_id, user.id)
    expense = session.get(Expense, expense_id)
    if expense is None or expense.group_id != group_id or expense.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    now = datetime.now(timezone.utc)
    expense.deleted_at = now
    expense.updated_at = now
    session.add(expense)
    record_event(
        session,
        group_id=group_id,
        kind="expense_deleted",
        actor_id=user.id,
        subject_id=expense.id,
        when=now,
    )
    session.commit()
