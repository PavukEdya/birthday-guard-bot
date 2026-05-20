from __future__ import annotations

import asyncio
import contextlib
import signal
from pathlib import Path

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.admin import admin_router
from app.bot.middlewares.admin_check import AdminCheckMiddleware
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.repositories.birthday_event_repo import BirthdayEventRepository
from app.services.birthday_service import BirthdayService
from app.services.google_sheets_service import GoogleSheetsService
from app.services.scheduler_service import SchedulerService
from app.services.telegram_service import TelegramService

logger = get_logger(__name__)


async def main() -> None:
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)
    try:
        await _run()
    except Exception as exc:
        logger.error("startup_failed", error=str(exc), exc_info=True)
        raise


async def _run() -> None:

    # Ensure DB directory exists
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row

        # Repositories
        repo = BirthdayEventRepository(db)
        await repo.init_db()

        # Bot
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher()

        # Services
        sheets_service = GoogleSheetsService(
            sheet_id=settings.google_sheet_id,
            credentials_json=settings.google_credentials_json,
        )
        telegram_service = TelegramService(
            bot=bot,
            group_chat_id=settings.group_chat_id,
        )
        birthday_service = BirthdayService(
            remove_before_days=settings.remove_before_days,
            return_after_days=settings.return_after_days,
        )
        scheduler = SchedulerService(
            sheets_service=sheets_service,
            telegram_service=telegram_service,
            birthday_service=birthday_service,
            repo=repo,
            timezone_name=settings.timezone,
            check_hour=settings.check_hour,
            check_minute=settings.check_minute,
        )

        # Inject dependencies into handler data
        dp["repo"] = repo
        dp["telegram_service"] = telegram_service

        # Middlewares and routers
        dp.message.middleware(AdminCheckMiddleware())
        dp.include_router(admin_router)

        # Graceful shutdown
        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()

        def _handle_signal(sig: int, _: object) -> None:
            logger.info("shutdown_signal_received", signal=sig)
            loop.call_soon_threadsafe(stop_event.set)

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, _handle_signal)

        # Startup
        scheduler.start()
        logger.info("bot_started")

        polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
        try:
            await stop_event.wait()
        finally:
            logger.info("shutdown_started")
            await dp.stop_polling()
            await polling_task
            await scheduler.shutdown()
            await bot.session.close()
            logger.info("bot_stopped")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())
