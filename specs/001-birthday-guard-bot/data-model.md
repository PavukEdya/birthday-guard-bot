# Data Model: Birthday Guard Bot

**Branch**: `001-birthday-guard-bot` | **Date**: 2026-05-18

---

## Entities

### Employee (in-memory, sourced from Google Sheets)

Represents a single row read from the Google Sheet. Not persisted in SQLite.
Validated on ingest; invalid rows are skipped and logged.

```python
class Employee(BaseModel):
    tg_username: str        # without leading @; non-empty
    full_name: str          # non-empty display name
    birth_date: date        # parsed from "dd.mm.yyyy" format
    wishes: str | None      # optional; empty string normalized to None
    comment: str | None     # optional; empty string normalized to None
```

**Validation rules**:
- `tg_username`: stripped, lowercased, non-empty after stripping.
- `birth_date`: strictly parsed from `dd.mm.yyyy`; any other format → skip row.
- `wishes` / `comment`: empty strings and whitespace-only values normalized to `None`.

---

### BirthdayEvent (persisted in SQLite)

Represents one bot-managed removal/restoration cycle for a given employee in a
given calendar year. Guards idempotency.

```python
class EventStatus(str, Enum):
    REMOVED = "removed"
    RESTORED = "restored"

class BirthdayEvent(BaseModel):
    id: int                 # PRIMARY KEY AUTOINCREMENT
    username: str           # tg_username (no @)
    birth_date: str         # original "dd.mm.yyyy" string for auditability
    year: int               # calendar year this event belongs to
    removed_at: datetime | None   # UTC timestamp of removal
    restored_at: datetime | None  # UTC timestamp of restoration
    status: EventStatus     # current state
```

**Unique constraint**: `(username, year)` — one event record per employee per year.

---

## State Machine

```
[no record]
     │
     │  daily job: birthday is REMOVE_BEFORE_DAYS away
     ▼
  REMOVED ──────────────────────────────────────────────────────────────────┐
     │                                                                      │
     │  (FR-005a) daily job: employee detected back in group                │
     │  before birthday passes → re-execute banChatMember                  │
     │  (status stays REMOVED, no new DB record)                           │
     ◄──────────────────────────────────────────────────────────────────────┘
     │
     │  daily job: birthday was RETURN_AFTER_DAYS ago
     │  OR admin runs /add_all
     ▼
  RESTORED (terminal for this year)
```

**Notes**:
- Re-removal (FR-005a) does not create a new DB record; it re-executes the Telegram
  API call against the existing `REMOVED` record.
- Once `RESTORED`, no further automatic action is taken for that `(username, year)` pair.
- The next calendar year produces a new record (different `year` value).

---

## SQL Schema

```sql
CREATE TABLE IF NOT EXISTS birthday_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    birth_date  TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    removed_at  TEXT,                   -- ISO-8601 UTC datetime or NULL
    restored_at TEXT,                   -- ISO-8601 UTC datetime or NULL
    status      TEXT    NOT NULL CHECK (status IN ('removed', 'restored')),
    UNIQUE (username, year)
);

CREATE INDEX IF NOT EXISTS idx_birthday_events_status
    ON birthday_events (status);

CREATE INDEX IF NOT EXISTS idx_birthday_events_username
    ON birthday_events (username);
```

---

## Repository Interface

```python
class BirthdayEventRepository:
    async def get_by_username_year(
        self, username: str, year: int
    ) -> BirthdayEvent | None: ...

    async def create_removed(
        self, username: str, birth_date: str, year: int, removed_at: datetime
    ) -> BirthdayEvent: ...

    async def mark_restored(
        self, username: str, year: int, restored_at: datetime
    ) -> None: ...

    async def list_removed(self) -> list[BirthdayEvent]: ...
```

---

## Google Sheets Format

The sheet MUST have a header row followed by data rows. Column order is fixed:

| Column index | Field name   | Required | Notes                        |
|--------------|--------------|----------|------------------------------|
| 0            | tg_username  | Yes      | Telegram username without @  |
| 1            | full_name    | Yes      | Display name                 |
| 2            | birth_date   | Yes      | Strict format: dd.mm.yyyy    |
| 3            | wishes       | No       | Empty string → None          |
| 4            | comment      | No       | Empty string → None          |

Rows where `tg_username`, `full_name`, or `birth_date` are empty or malformed
are skipped and a warning is logged. Processing continues for all remaining rows.
