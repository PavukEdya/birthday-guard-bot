from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.models.birthday_event import BirthdayEvent, EventStatus

if TYPE_CHECKING:
    import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS birthday_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    birth_date  TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    removed_at  TEXT,
    restored_at TEXT,
    status      TEXT    NOT NULL CHECK (status IN ('removed', 'restored')),
    UNIQUE (username, year)
);

CREATE INDEX IF NOT EXISTS idx_birthday_events_status
    ON birthday_events (status);

CREATE INDEX IF NOT EXISTS idx_birthday_events_username
    ON birthday_events (username);
"""


def _row_to_event(row: aiosqlite.Row) -> BirthdayEvent:
    def _parse_dt(val: str | None) -> datetime | None:
        if val is None:
            return None
        return datetime.fromisoformat(val)

    return BirthdayEvent(
        id=row[0],
        username=row[1],
        birth_date=row[2],
        year=row[3],
        removed_at=_parse_dt(row[4]),
        restored_at=_parse_dt(row[5]),
        status=EventStatus(row[6]),
    )


class BirthdayEventRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def init_db(self) -> None:
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def get_by_username_year(self, username: str, year: int) -> BirthdayEvent | None:
        cursor = await self._db.execute(
            "SELECT id, username, birth_date, year, removed_at, restored_at, status "
            "FROM birthday_events WHERE username = ? AND year = ?",
            (username, year),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_event(row)

    async def create_removed(
        self,
        username: str,
        birth_date: str,
        year: int,
        removed_at: datetime,
    ) -> BirthdayEvent:
        cursor = await self._db.execute(
            "INSERT INTO birthday_events (username, birth_date, year, removed_at, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, birth_date, year, removed_at.isoformat(), EventStatus.REMOVED.value),
        )
        await self._db.commit()
        row_id = cursor.lastrowid
        event = await self.get_by_username_year(username, year)
        assert event is not None and event.id == row_id  # guaranteed by INSERT above
        return event

    async def mark_restored(self, username: str, year: int, restored_at: datetime) -> None:
        await self._db.execute(
            "UPDATE birthday_events SET status = ?, restored_at = ? "
            "WHERE username = ? AND year = ?",
            (EventStatus.RESTORED.value, restored_at.isoformat(), username, year),
        )
        await self._db.commit()

    async def list_removed(self) -> list[BirthdayEvent]:
        cursor = await self._db.execute(
            "SELECT id, username, birth_date, year, removed_at, restored_at, status "
            "FROM birthday_events WHERE status = ?",
            (EventStatus.REMOVED.value,),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]
