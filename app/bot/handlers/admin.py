from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from app.core.logging import get_logger

if TYPE_CHECKING:
    from aiogram.types import Message

    from app.repositories.birthday_event_repo import BirthdayEventRepository
    from app.services.telegram_service import TelegramService

admin_router = Router(name="admin")
logger = get_logger(__name__)


@admin_router.message(Command("add_all"))
async def add_all_handler(
    message: Message,
    repo: BirthdayEventRepository,
    telegram_service: TelegramService,
) -> None:
    removed = await repo.list_removed()
    if not removed:
        await message.reply("Нет сотрудников для возврата.")
        return

    now_utc = datetime.now(tz=UTC)
    count = 0
    for event in removed:
        success = await telegram_service.restore_user(event.username)
        if success:
            await repo.mark_restored(event.username, event.year, now_utc)
            count += 1
            logger.info("add_all_restored", username=event.username)

    await message.reply(f"Восстановлено сотрудников: {count}.")
    logger.info("add_all_complete", count=count)
