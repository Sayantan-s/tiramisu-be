from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Field, SQLModel


def default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class Invite(SQLModel, table=True):
    code: str = Field(primary_key=True)
    group_id: UUID = Field(foreign_key="group.id", index=True)
    created_by: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=default_expires_at)
    max_uses: int = 5
    used_count: int = 0
