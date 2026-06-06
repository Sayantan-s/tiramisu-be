from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Event(SQLModel, table=True):
    """kind ∈ {expense_added, expense_updated, expense_deleted,
                settlement_recorded, settlement_deleted,
                comment, member_joined, month_closed}."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    group_id: UUID = Field(foreign_key="group.id", index=True)
    month: str = Field(index=True)  # "YYYY-MM"
    kind: str
    actor_id: UUID
    subject_id: UUID | None = None
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
