from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from enum import StrEnum

from pydantic import BaseModel


class EventStatus(StrEnum):
    REMOVED = "removed"
    RESTORED = "restored"


class BirthdayEvent(BaseModel):
    id: int
    username: str
    birth_date: str
    year: int
    removed_at: datetime | None
    restored_at: datetime | None
    status: EventStatus
