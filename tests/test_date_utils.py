from __future__ import annotations

from datetime import date

from app.utils.date_utils import days_since_birthday, days_until_birthday


class TestDaysUntilBirthday:
    def test_birthday_is_today(self) -> None:
        today = date(2024, 5, 18)
        birth = date(1990, 5, 18)
        assert days_until_birthday(birth, today) == 0

    def test_birthday_tomorrow(self) -> None:
        today = date(2024, 5, 18)
        birth = date(1990, 5, 19)
        assert days_until_birthday(birth, today) == 1

    def test_birthday_in_future_same_year(self) -> None:
        today = date(2024, 3, 1)
        birth = date(1990, 5, 18)
        assert days_until_birthday(birth, today) == (date(2024, 5, 18) - today).days

    def test_birthday_already_passed_this_year_wraps_to_next(self) -> None:
        today = date(2024, 5, 19)
        birth = date(1990, 5, 18)
        expected = (date(2025, 5, 18) - today).days
        assert days_until_birthday(birth, today) == expected

    def test_birthday_wraps_year_boundary_december_to_january(self) -> None:
        today = date(2024, 12, 30)
        birth = date(1990, 1, 2)
        assert days_until_birthday(birth, today) == 3

    def test_feb29_in_leap_year_is_exact(self) -> None:
        today = date(2024, 2, 26)
        birth = date(1992, 2, 29)
        assert days_until_birthday(birth, today) == 3

    def test_feb29_in_non_leap_year_treated_as_mar1(self) -> None:
        today = date(2023, 2, 26)
        birth = date(1992, 2, 29)
        # Non-leap 2023: Feb 29 → Mar 1, so 3 days until Mar 1
        assert days_until_birthday(birth, today) == 3

    def test_feb29_already_passed_in_non_leap_year_next_occurrence_is_mar1_next_year(self) -> None:
        today = date(2023, 3, 5)
        birth = date(1992, 2, 29)
        # Mar 1 2023 already passed; next is Mar 1 2024 (leap year, so Feb 29 2024)
        next_occ = date(2024, 2, 29)
        assert days_until_birthday(birth, today) == (next_occ - today).days


class TestDaysSinceBirthday:
    def test_birthday_is_today(self) -> None:
        today = date(2024, 5, 18)
        birth = date(1990, 5, 18)
        assert days_since_birthday(birth, today) == 0

    def test_birthday_was_yesterday(self) -> None:
        today = date(2024, 5, 19)
        birth = date(1990, 5, 18)
        assert days_since_birthday(birth, today) == 1

    def test_birthday_not_yet_this_year_looks_at_last_year(self) -> None:
        today = date(2024, 3, 1)
        birth = date(1990, 5, 18)
        expected = (today - date(2023, 5, 18)).days
        assert days_since_birthday(birth, today) == expected

    def test_birthday_was_exactly_return_after_days_ago(self) -> None:
        today = date(2024, 5, 20)
        birth = date(1990, 5, 18)
        assert days_since_birthday(birth, today) == 2

    def test_feb29_non_leap_year_treated_as_mar1(self) -> None:
        today = date(2023, 3, 3)
        birth = date(1992, 2, 29)
        # Mar 1 2023 was 2 days ago
        assert days_since_birthday(birth, today) == 2
