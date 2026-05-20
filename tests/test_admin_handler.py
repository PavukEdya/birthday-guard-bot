from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.birthday_event import BirthdayEvent, EventStatus
from app.repositories.birthday_event_repo import BirthdayEventRepository  # noqa: TCH001


def _make_event(username: str = "ivan_petrov", year: int = 2024) -> BirthdayEvent:
    return BirthdayEvent(
        id=1,
        username=username,
        birth_date="18.05.1990",
        year=year,
        removed_at=datetime(2024, 5, 15, 9, 0),
        restored_at=None,
        status=EventStatus.REMOVED,
    )


class TestAddAllHandler:
    async def test_add_all_restores_all_and_replies_count(
        self, repo: BirthdayEventRepository
    ) -> None:
        from app.bot.handlers.admin import add_all_handler

        # Insert two removed events
        await repo.create_removed("ivan_petrov", "18.05.1990", 2024, datetime(2024, 5, 15, 9, 0))
        await repo.create_removed("anna_smith", "20.03.1988", 2024, datetime(2024, 5, 15, 9, 0))

        mock_telegram = MagicMock()
        mock_telegram.restore_user = AsyncMock(return_value=True)

        mock_message = MagicMock()
        mock_message.reply = AsyncMock()

        with patch("app.bot.handlers.admin.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 5, 20, 9, 0)
            await add_all_handler(mock_message, repo, mock_telegram)

        mock_message.reply.assert_called_once()
        reply_text: str = mock_message.reply.call_args[0][0]
        assert "2" in reply_text
        assert mock_telegram.restore_user.call_count == 2

    async def test_add_all_replies_nothing_to_restore_when_none_removed(
        self, repo: BirthdayEventRepository
    ) -> None:
        from app.bot.handlers.admin import add_all_handler

        mock_telegram = MagicMock()
        mock_message = MagicMock()
        mock_message.reply = AsyncMock()

        await add_all_handler(mock_message, repo, mock_telegram)

        mock_message.reply.assert_called_once()
        reply_text: str = mock_message.reply.call_args[0][0]
        assert "Нет" in reply_text or "0" in reply_text or "нет" in reply_text.lower()

    async def test_add_all_does_not_broadcast_to_group(
        self, repo: BirthdayEventRepository
    ) -> None:
        from app.bot.handlers.admin import add_all_handler

        await repo.create_removed("ivan_petrov", "18.05.1990", 2024, datetime(2024, 5, 15, 9, 0))

        mock_telegram = MagicMock()
        mock_telegram.restore_user = AsyncMock(return_value=True)
        mock_telegram.send_message = AsyncMock()

        mock_message = MagicMock()
        mock_message.reply = AsyncMock()

        with patch("app.bot.handlers.admin.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 5, 20, 9, 0)
            await add_all_handler(mock_message, repo, mock_telegram)

        # send_message (group broadcast) must NOT be called
        mock_telegram.send_message.assert_not_called()
