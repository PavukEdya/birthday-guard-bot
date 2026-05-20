from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.utils.date_utils import days_since_birthday, days_until_birthday

if TYPE_CHECKING:
    from app.models.birthday_event import BirthdayEvent
    from app.models.employee import Employee


class BirthdayService:
    def __init__(self, remove_before_days: int, return_after_days: int) -> None:
        self._remove_before_days = remove_before_days
        self._return_after_days = return_after_days

    def get_employees_to_remove(
        self, employees: list[Employee], today: date
    ) -> dict[date, list[Employee]]:
        """
        Return employees whose birthday is exactly remove_before_days away,
        grouped by their birthday date (month/day in the current year).
        """
        grouped: dict[date, list[Employee]] = {}
        for emp in employees:
            days = days_until_birthday(emp.birth_date, today)
            if days == self._remove_before_days:
                birthday_key = date(today.year, emp.birth_date.month, emp.birth_date.day)
                # Handle Feb 29 in non-leap year
                try:
                    birthday_key = date(
                        today.year + (1 if days > 0 and emp.birth_date.month < today.month else 0),
                        emp.birth_date.month,
                        emp.birth_date.day,
                    )
                except ValueError:
                    birthday_key = date(
                        today.year + (1 if days > 0 and emp.birth_date.month < today.month else 0),
                        3,
                        1,
                    )
                grouped.setdefault(birthday_key, []).append(emp)
        return grouped

    def get_employees_to_restore(
        self, removed_events: list[BirthdayEvent], today: date
    ) -> list[BirthdayEvent]:
        """Return removed events where the birthday was return_after_days ago or more."""
        result: list[BirthdayEvent] = []
        for event in removed_events:
            day_str, month_str, year_str = event.birth_date.split(".")
            birth = date(int(year_str), int(month_str), int(day_str))
            days = days_since_birthday(birth, today)
            if days >= self._return_after_days:
                result.append(event)
        return result

    def get_employees_for_reremoval(
        self,
        employees: list[Employee],
        removed_events: list[BirthdayEvent],
        current_members: set[str],
        today: date,
    ) -> list[Employee]:
        """
        FR-005a: Return employees who are in removed state but detected back in the group
        before their birthday has passed.
        """
        removed_usernames = {
            e.username
            for e in removed_events
            if days_since_birthday(
                date(*reversed([int(x) for x in e.birth_date.split(".")])), today  # type: ignore[arg-type]
            )
            == 0
            or days_until_birthday(
                date(*reversed([int(x) for x in e.birth_date.split(".")])), today  # type: ignore[arg-type]
            )
            > 0
        }
        reremove: list[Employee] = []
        for emp in employees:
            if emp.tg_username in removed_usernames and emp.tg_username in current_members:
                reremove.append(emp)
        return reremove

    @staticmethod
    def build_notification_message(
        days_until: int, employees: list[Employee]
    ) -> str:
        lines = [f"🎉 Скоро день рождения!\n\nЧерез {days_until} дн. день рождения у:\n"]  # noqa: RUF001
        for emp in employees:
            lines.append(f"<b>{emp.full_name}</b> (@{emp.tg_username})")
            if emp.wishes:
                lines.append(f"\n🎁 Пожелания:\n{emp.wishes}")
            if emp.comment:
                lines.append(f"\n💬 Комментарий:\n{emp.comment}")
            lines.append("")
        return "\n".join(lines).strip()
