from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.repositories.birthday_event_repo import BirthdayEventRepository
    from app.services.birthday_service import BirthdayService
    from app.services.google_sheets_service import GoogleSheetsService
    from app.services.telegram_service import TelegramService

logger = get_logger(__name__)


class SchedulerService:
    def __init__(
        self,
        sheets_service: GoogleSheetsService,
        telegram_service: TelegramService,
        birthday_service: BirthdayService,
        repo: BirthdayEventRepository,
        timezone_name: str,
        check_hour: int,
        check_minute: int,
    ) -> None:
        self._sheets = sheets_service
        self._telegram = telegram_service
        self._birthday = birthday_service
        self._repo = repo
        self._tz = pytz.timezone(timezone_name)
        self._check_hour = check_hour
        self._check_minute = check_minute
        self._scheduler = AsyncIOScheduler(timezone=self._tz)

    def start(self) -> None:
        self._scheduler.add_job(
            self._daily_job,
            CronTrigger(hour=self._check_hour, minute=self._check_minute, timezone=self._tz),
            id="daily_birthday_check",
            max_instances=1,
            misfire_grace_time=3600,
            coalesce=True,
            replace_existing=True,
        )
        self._scheduler.start()
        job = self._scheduler.get_job("daily_birthday_check")
        next_run = str(job.next_run_time) if job else "unknown"
        logger.info(
            "scheduler_started",
            timezone=str(self._tz),
            hour=self._check_hour,
            minute=self._check_minute,
            next_run=next_run,
        )

    async def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    async def _daily_job(self) -> None:
        now_utc = datetime.now(tz=UTC)
        today = datetime.now(tz=self._tz).date()
        logger.info("daily_job_start", date=str(today))

        if not await self._telegram.check_bot_is_admin():
            logger.error("daily_job_aborted", reason="bot is not admin")
            return

        # ── Step 1: Fetch employees ────────────────────────────────────────
        try:
            employees = await self._sheets.fetch_employees()
        except Exception as exc:
            logger.error("sheets_fetch_failed", error=str(exc))
            return

        # ── Step 2: Re-removal check (FR-005a) ────────────────────────────
        removed_events = await self._repo.list_removed()
        for event in removed_events:
            day, month, yr = (int(x) for x in event.birth_date.split("."))
            from datetime import date as dt_date

            birth = dt_date(yr, month, day)
            from app.utils.date_utils import days_until_birthday

            if days_until_birthday(birth, today) > 0:  # birthday not yet passed
                still_member = await self._telegram.is_member(event.username)
                if still_member:
                    logger.info("re_removing_user", username=event.username)
                    await self._telegram.ban_and_unban(event.username)

        # ── Step 3: Removal of upcoming birthdays ─────────────────────────
        to_remove = self._birthday.get_employees_to_remove(employees, today)
        newly_removed: list[tuple[int, list[Employee]]] = []

        for birthday_date, emps in to_remove.items():
            days_until = self._birthday._remove_before_days
            removed_in_group: list[Employee] = []
            for emp in emps:
                existing = await self._repo.get_by_username_year(emp.tg_username, today.year)
                if existing is not None:
                    logger.info("skip_already_removed", username=emp.tg_username, year=today.year)
                    continue
                success = await self._telegram.ban_and_unban(emp.tg_username)
                if success:
                    await self._repo.create_removed(
                        username=emp.tg_username,
                        birth_date=emp.birth_date.strftime("%d.%m.%Y"),
                        year=today.year,
                        removed_at=now_utc,
                    )
                    removed_in_group.append(emp)
                    logger.info(
                        "user_removed_for_birthday",
                        username=emp.tg_username,
                        birthday=str(birthday_date),
                    )
            if removed_in_group:
                newly_removed.append((days_until, removed_in_group))

        # ── Step 4: Send combined notifications ───────────────────────────
        for days_until, emps in newly_removed:
            message = self._birthday.build_notification_message(days_until, emps)
            await self._telegram.send_message(message)
            logger.info("notification_sent", count=len(emps))

        # ── Step 5: Restore employees past their birthday ─────────────────
        removed_events = await self._repo.list_removed()
        to_restore = self._birthday.get_employees_to_restore(removed_events, today)
        for event in to_restore:
            success = await self._telegram.restore_user(event.username)
            if success:
                await self._repo.mark_restored(event.username, event.year, now_utc)
                logger.info("user_restored_after_birthday", username=event.username)

        logger.info("daily_job_complete", date=str(today))
