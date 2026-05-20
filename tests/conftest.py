from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
import pytest_asyncio

from app.repositories.birthday_event_repo import BirthdayEventRepository


@pytest_asyncio.fixture
async def db() -> aiosqlite.Connection:  # type: ignore[misc]
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        repo = BirthdayEventRepository(conn)
        await repo.init_db()
        yield conn


@pytest_asyncio.fixture
async def repo(db: aiosqlite.Connection) -> BirthdayEventRepository:
    return BirthdayEventRepository(db)


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.get_chat_administrators = AsyncMock()
    bot.send_message = AsyncMock()
    return bot
