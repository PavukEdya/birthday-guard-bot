from __future__ import annotations

import calendar
from datetime import date


def _normalize_for_year(birth_date: date, year: int) -> date:
    """Return birth_date adjusted to the given year, mapping Feb 29 → Mar 1 in non-leap years."""
    if birth_date.month == 2 and birth_date.day == 29 and not calendar.isleap(year):
        return date(year, 3, 1)
    return date(year, birth_date.month, birth_date.day)


def days_until_birthday(birth_date: date, today: date) -> int:
    """
    Return the number of days from today until the next occurrence of birth_date.

    Feb 29 birthdays are treated as Mar 1 in non-leap years.
    Returns 0 if the birthday is today.
    """
    this_year = _normalize_for_year(birth_date, today.year)
    if this_year >= today:
        return (this_year - today).days

    next_year = _normalize_for_year(birth_date, today.year + 1)
    return (next_year - today).days


def days_since_birthday(birth_date: date, today: date) -> int:
    """
    Return the number of days since the most recent occurrence of birth_date.

    Feb 29 birthdays are treated as Mar 1 in non-leap years.
    Returns 0 if the birthday is today.
    """
    this_year = _normalize_for_year(birth_date, today.year)
    if this_year <= today:
        return (today - this_year).days

    last_year = _normalize_for_year(birth_date, today.year - 1)
    return (today - last_year).days


def birthday_year_for_removal(birth_date: date, today: date, remove_before_days: int) -> int:
    """
    Return the calendar year the birthday event belongs to, given that removal
    fires remove_before_days days before the birthday.
    """
    next_birthday = today + __import__("datetime").timedelta(days=remove_before_days)
    candidate = _normalize_for_year(birth_date, next_birthday.year)
    if candidate == next_birthday:
        return next_birthday.year
    # Fallback: the birthday is within the look-ahead window crossing a year boundary
    return next_birthday.year
