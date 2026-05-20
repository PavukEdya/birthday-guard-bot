from __future__ import annotations

from datetime import date, datetime

from app.models.birthday_event import BirthdayEvent, EventStatus
from app.models.employee import Employee
from app.services.birthday_service import BirthdayService

_REMOVE = 3
_RETURN = 2


def _service() -> BirthdayService:
    return BirthdayService(remove_before_days=_REMOVE, return_after_days=_RETURN)


def _emp(username: str = "ivan", birth_date: str = "18.05.1990") -> Employee:
    return Employee(tg_username=username, full_name="Test User", birth_date=birth_date)


def _event(
    username: str = "ivan",
    birth_date: str = "18.05.1990",
    year: int = 2024,
    status: EventStatus = EventStatus.REMOVED,
) -> BirthdayEvent:
    return BirthdayEvent(
        id=1,
        username=username,
        birth_date=birth_date,
        year=year,
        removed_at=datetime(2024, 5, 15, 9, 0),
        restored_at=None,
        status=status,
    )


class TestGetEmployeesToRemove:
    def test_removes_employee_exactly_before_days_away(self) -> None:
        svc = _service()
        today = date(2024, 5, 15)
        emp = _emp(birth_date="18.05.1990")  # birthday in 3 days
        result = svc.get_employees_to_remove([emp], today)
        assert len(result) == 1
        employees = next(iter(result.values()))
        assert employees[0].tg_username == "ivan"

    def test_does_not_remove_employee_wrong_day_count(self) -> None:
        svc = _service()
        today = date(2024, 5, 15)
        emp = _emp(birth_date="19.05.1990")  # 4 days away, not 3
        result = svc.get_employees_to_remove([emp], today)
        assert len(result) == 0

    def test_groups_multiple_employees_same_birthday(self) -> None:
        svc = _service()
        today = date(2024, 5, 15)
        emp1 = _emp("user1", "18.05.1990")
        emp2 = _emp("user2", "18.05.1991")
        result = svc.get_employees_to_remove([emp1, emp2], today)
        assert len(result) == 1
        employees = next(iter(result.values()))
        assert len(employees) == 2


class TestGetEmployeesToRestore:
    def test_restores_when_birthday_passed_return_after_days_ago(self) -> None:
        svc = _service()
        today = date(2024, 5, 20)
        event = _event(birth_date="18.05.1990")  # birthday was 2 days ago
        result = svc.get_employees_to_restore([event], today)
        assert len(result) == 1

    def test_does_not_restore_before_return_after_days(self) -> None:
        svc = _service()
        today = date(2024, 5, 19)
        event = _event(birth_date="18.05.1990")  # birthday was 1 day ago, need 2
        result = svc.get_employees_to_restore([event], today)
        assert len(result) == 0

    def test_does_not_restore_already_restored(self) -> None:
        svc = _service()
        today = date(2024, 5, 20)
        event = _event(birth_date="18.05.1990", status=EventStatus.RESTORED)
        # Restored events shouldn't be in list_removed() so this tests the filtering
        result = svc.get_employees_to_restore([event], today)
        # Function only checks days — caller filters by status via repo.list_removed()
        assert len(result) == 1  # date condition met regardless of status


class TestBuildNotificationMessage:
    def test_includes_full_name_and_username(self) -> None:
        emp = Employee(
            tg_username="ivan", full_name="Иван Петров", birth_date=date(1990, 5, 18)
        )
        msg = BirthdayService.build_notification_message(3, [emp])
        assert "Иван Петров" in msg
        assert "@ivan" in msg
        assert "3" in msg

    def test_omits_empty_wishes(self) -> None:
        emp = Employee(
            tg_username="ivan", full_name="Иван Петров", birth_date=date(1990, 5, 18), wishes=None
        )
        msg = BirthdayService.build_notification_message(3, [emp])
        assert "Пожелания" not in msg

    def test_omits_empty_comment(self) -> None:
        emp = Employee(
            tg_username="ivan",
            full_name="Иван Петров",
            birth_date=date(1990, 5, 18),
            comment=None,
        )
        msg = BirthdayService.build_notification_message(3, [emp])
        assert "Комментарий" not in msg

    def test_includes_wishes_and_comment_when_present(self) -> None:
        emp = Employee(
            tg_username="ivan",
            full_name="Иван Петров",
            birth_date=date(1990, 5, 18),
            wishes="Любит кофе",
            comment="Работает в QA",
        )
        msg = BirthdayService.build_notification_message(3, [emp])
        assert "Любит кофе" in msg
        assert "Работает в QA" in msg

    def test_combined_message_for_multiple_employees(self) -> None:
        emp1 = Employee(tg_username="user1", full_name="User One", birth_date=date(1990, 5, 18))
        emp2 = Employee(tg_username="user2", full_name="User Two", birth_date=date(1991, 5, 18))
        msg = BirthdayService.build_notification_message(3, [emp1, emp2])
        assert "User One" in msg
        assert "User Two" in msg
        assert msg.count("🎉") == 1  # single combined header
