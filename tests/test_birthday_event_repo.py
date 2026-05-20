from __future__ import annotations

from datetime import datetime

import aiosqlite
import pytest

from app.models.birthday_event import EventStatus
from app.repositories.birthday_event_repo import BirthdayEventRepository  # noqa: TCH001

_NOW = datetime(2024, 5, 15, 9, 0, 0)
_BIRTH_DATE = "21.05.1991"
_USERNAME = "ivan_petrov"
_YEAR = 2024


class TestCreateRemoved:
    async def test_create_removed_success(self, repo: BirthdayEventRepository) -> None:
        event = await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        assert event.username == _USERNAME
        assert event.birth_date == _BIRTH_DATE
        assert event.year == _YEAR
        assert event.status == EventStatus.REMOVED
        assert event.removed_at == _NOW
        assert event.restored_at is None

    async def test_create_removed_duplicate_raises_integrity_error(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        with pytest.raises(aiosqlite.IntegrityError):
            await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)


class TestGetByUsernameYear:
    async def test_get_by_username_year_found(self, repo: BirthdayEventRepository) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        event = await repo.get_by_username_year(_USERNAME, _YEAR)
        assert event is not None
        assert event.username == _USERNAME
        assert event.year == _YEAR

    async def test_get_by_username_year_not_found(self, repo: BirthdayEventRepository) -> None:
        result = await repo.get_by_username_year("nonexistent", _YEAR)
        assert result is None

    async def test_get_by_username_year_different_year_not_found(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        result = await repo.get_by_username_year(_USERNAME, _YEAR + 1)
        assert result is None


class TestListRemoved:
    async def test_list_removed_returns_only_removed_status(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        await repo.create_removed("anna_smith", "15.03.1988", _YEAR, _NOW)
        # Restore one
        restored_at = datetime(2024, 5, 23, 9, 0, 0)
        await repo.mark_restored("anna_smith", _YEAR, restored_at)

        removed = await repo.list_removed()
        assert len(removed) == 1
        assert removed[0].username == _USERNAME

    async def test_list_removed_empty_when_none(self, repo: BirthdayEventRepository) -> None:
        removed = await repo.list_removed()
        assert removed == []

    async def test_list_removed_excludes_restored_records(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        await repo.mark_restored(_USERNAME, _YEAR, datetime(2024, 5, 23, 9, 0, 0))
        removed = await repo.list_removed()
        assert removed == []


class TestMarkRestored:
    async def test_mark_restored_transitions_status(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        restored_at = datetime(2024, 5, 23, 9, 0, 0)
        await repo.mark_restored(_USERNAME, _YEAR, restored_at)

        event = await repo.get_by_username_year(_USERNAME, _YEAR)
        assert event is not None
        assert event.status == EventStatus.RESTORED

    async def test_mark_restored_sets_restored_at(
        self, repo: BirthdayEventRepository
    ) -> None:
        await repo.create_removed(_USERNAME, _BIRTH_DATE, _YEAR, _NOW)
        restored_at = datetime(2024, 5, 23, 9, 0, 0)
        await repo.mark_restored(_USERNAME, _YEAR, restored_at)

        event = await repo.get_by_username_year(_USERNAME, _YEAR)
        assert event is not None
        assert event.restored_at == restored_at
