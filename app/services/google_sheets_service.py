from __future__ import annotations

import json
from typing import Any

import gspread
from pydantic import ValidationError
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.models.employee import Employee

logger = get_logger(__name__)


class GoogleSheetsService:
    def __init__(self, sheet_id: str, credentials_json: str) -> None:
        self._sheet_id = sheet_id
        self._credentials_json = credentials_json
        self._client: gspread.Client | None = None

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds_dict: dict[str, Any] = json.loads(self._credentials_json)
            self._client = gspread.service_account_from_dict(creds_dict)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, 20),  # logging.DEBUG = 10, INFO = 20
        reraise=True,
    )
    async def fetch_employees(self) -> list[Employee]:
        client = self._get_client()
        sheet = client.open_by_key(self._sheet_id).sheet1
        records: list[dict[str, str]] = sheet.get_all_records()

        employees: list[Employee] = []
        for idx, record in enumerate(records, start=2):  # row 1 is header
            try:
                emp = Employee(
                    tg_username=record.get("tg_username", ""),
                    full_name=record.get("full_name", ""),
                    birth_date=record.get("birth_date", ""),
                    wishes=record.get("wishes") or None,
                    comment=record.get("comment") or None,
                )
                employees.append(emp)
            except (ValidationError, ValueError) as exc:
                logger.warning(
                    "row_skipped",
                    row=idx,
                    username=record.get("tg_username", ""),
                    reason=str(exc),
                )
        logger.info("employees_fetched", count=len(employees))
        return employees
