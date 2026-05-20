from __future__ import annotations

import json
import os
from pathlib import Path

import pytz
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str
    group_chat_id: int

    # Google Sheets
    google_sheet_id: str
    google_credentials_json: str  # file path OR raw JSON string

    # Birthday logic
    remove_before_days: int = 3
    return_after_days: int = 2

    # Scheduler
    timezone: str = "Europe/Moscow"
    check_hour: int = 9
    check_minute: int = 0

    # Storage
    db_path: str = "data/birthday_guard.db"

    # Logging
    log_format: str = "json"
    log_level: str = "INFO"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError as exc:
            raise ValueError(f"Unknown timezone: {v}") from exc
        return v

    @field_validator("check_hour")
    @classmethod
    def validate_hour(cls, v: int) -> int:
        if not 0 <= v <= 23:
            raise ValueError("check_hour must be between 0 and 23")
        return v

    @field_validator("check_minute")
    @classmethod
    def validate_minute(cls, v: int) -> int:
        if not 0 <= v <= 59:
            raise ValueError("check_minute must be between 0 and 59")
        return v

    @model_validator(mode="after")
    def resolve_credentials(self) -> Settings:
        cred = self.google_credentials_json.strip()
        # If it's a file path, read the file
        if not cred.startswith("{") and os.path.isfile(cred):
            self.google_credentials_json = Path(cred).read_text(encoding="utf-8")
        # Validate it's parseable JSON
        try:
            json.loads(self.google_credentials_json)
        except json.JSONDecodeError as exc:
            raise ValueError("GOOGLE_CREDENTIALS_JSON is not valid JSON") from exc
        return self


settings = Settings()  # type: ignore[call-arg]
