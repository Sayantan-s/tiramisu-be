from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Group(SQLModel, table=True):
    """kind ∈ {'roomies', 'trips'} — enforced at the API boundary via Pydantic Literal."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: str = Field(index=True)
    name: str
    icon: str | None = None
    created_by: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroupMember(SQLModel, table=True):
    """role ∈ {'owner', 'member'} — enforced at the API boundary."""

    group_id: UUID = Field(foreign_key="group.id", primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role: str = "member"
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
