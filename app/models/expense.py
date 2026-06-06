from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Expense(SQLModel, table=True):
    """source ∈ {'manual','receipt','sms'}; split is a SplitRule shape (see lib/split.py)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    group_id: UUID = Field(foreign_key="group.id", index=True)
    amount: int
    currency: str = "INR"
    payer_id: UUID
    paid_at: datetime
    category: str
    description: str | None = None
    receipt_uri: str | None = None
    source: str = "manual"
    split: dict = Field(default_factory=dict, sa_column=Column(JSON))
    recurring: dict | None = Field(default=None, sa_column=Column(JSON))
    created_by: UUID
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    deleted_at: datetime | None = None


class Settlement(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    group_id: UUID = Field(foreign_key="group.id", index=True)
    from_id: UUID
    to_id: UUID
    amount: int
    paid_at: datetime
    note: str | None = None
    created_by: UUID
    created_at: datetime = Field(default_factory=_utcnow)
    deleted_at: datetime | None = None
