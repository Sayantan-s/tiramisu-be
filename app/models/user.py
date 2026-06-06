from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: str = Field(unique=True, index=True)
    name: str
    avatar: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
