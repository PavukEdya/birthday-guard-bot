from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.models.employee import Employee


def _make_row(
    username: str = "ivan_petrov",
    full_name: str = "Иван Петров",
    birth_date: str = "21.05.1991",
    wishes: str = "Любит кофе",
    comment: str = "Работает в QA",
) -> dict[str, str]:
    return {
        "tg_username": username,
        "full_name": full_name,
        "birth_date": birth_date,
        "wishes": wishes,
        "comment": comment,
    }


class TestEmployeeModelParsing:
    """Tests for Employee model parsing (row validation logic)."""

    def test_parse_valid_row(self) -> None:
        row = _make_row()
        emp = Employee(**row)
        assert emp.tg_username == "ivan_petrov"
        assert emp.full_name == "Иван Петров"
        assert emp.birth_date == date(1991, 5, 21)
        assert emp.wishes == "Любит кофе"
        assert emp.comment == "Работает в QA"

    def test_parse_empty_wishes_normalized_to_none(self) -> None:
        row = _make_row(wishes="")
        emp = Employee(**row)
        assert emp.wishes is None

    def test_parse_whitespace_wishes_normalized_to_none(self) -> None:
        row = _make_row(wishes="   ")
        emp = Employee(**row)
        assert emp.wishes is None

    def test_parse_empty_comment_normalized_to_none(self) -> None:
        row = _make_row(comment="")
        emp = Employee(**row)
        assert emp.comment is None

    def test_parse_malformed_date_raises(self) -> None:
        from pydantic import ValidationError

        row = _make_row(birth_date="1991/05/21")
        with pytest.raises(ValidationError):
            Employee(**row)

    def test_parse_date_wrong_format_dashes_raises(self) -> None:
        from pydantic import ValidationError

        row = _make_row(birth_date="21-05-1991")
        with pytest.raises(ValidationError):
            Employee(**row)

    def test_parse_missing_username_raises(self) -> None:
        from pydantic import ValidationError

        row = _make_row(username="")
        with pytest.raises(ValidationError):
            Employee(**row)

    def test_parse_missing_full_name_raises(self) -> None:
        from pydantic import ValidationError

        row = _make_row(full_name="")
        with pytest.raises(ValidationError):
            Employee(**row)

    def test_username_at_prefix_stripped(self) -> None:
        row = _make_row(username="@ivan_petrov")
        emp = Employee(**row)
        assert emp.tg_username == "ivan_petrov"

    def test_username_lowercased(self) -> None:
        row = _make_row(username="IVAN_PETROV")
        emp = Employee(**row)
        assert emp.tg_username == "ivan_petrov"


class TestGetEmployeesSkipsBadRows:
    """Tests for GoogleSheetsService.fetch_employees row-skipping behaviour."""

    def test_get_employees_skips_bad_rows_and_continues(self) -> None:
        from app.services.google_sheets_service import GoogleSheetsService

        valid_row = _make_row()
        bad_row = _make_row(birth_date="not-a-date")

        mock_sheet = MagicMock()
        mock_sheet.get_all_records.return_value = [bad_row, valid_row]

        mock_client = MagicMock()
        mock_client.open_by_key.return_value.sheet1 = mock_sheet

        with patch("app.services.google_sheets_service.gspread") as mock_gspread:
            mock_gspread.service_account_from_dict.return_value = mock_client
            import json

            creds = json.dumps({"type": "service_account"})

            svc = GoogleSheetsService(sheet_id="sheet123", credentials_json=creds)
            # Inject the mock client directly
            svc._client = mock_client  # type: ignore[attr-defined]

            import asyncio

            employees = asyncio.get_event_loop().run_until_complete(svc.fetch_employees())

        assert len(employees) == 1
        assert employees[0].tg_username == "ivan_petrov"
