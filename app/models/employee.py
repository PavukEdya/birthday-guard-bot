from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator


class Employee(BaseModel):
    tg_username: str
    full_name: str
    birth_date: date
    wishes: str | None = None
    comment: str | None = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def parse_birth_date(cls, v: object) -> date:
        if isinstance(v, date):
            return v
        if not isinstance(v, str):
            raise ValueError("birth_date must be a string in dd.mm.yyyy format")
        try:
            day, month, year = v.strip().split(".")
            return date(int(year), int(month), int(day))
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"birth_date must be dd.mm.yyyy, got: {v!r}") from exc

    @field_validator("tg_username", mode="before")
    @classmethod
    def clean_username(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("tg_username must be a string")
        cleaned = v.strip().lstrip("@").lower()
        if not cleaned:
            raise ValueError("tg_username must not be empty")
        return cleaned

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_full_name(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("full_name must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("full_name must not be empty")
        return stripped

    @field_validator("wishes", "comment", mode="before")
    @classmethod
    def normalize_optional_str(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return None
