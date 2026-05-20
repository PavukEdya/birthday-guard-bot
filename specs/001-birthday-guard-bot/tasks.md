---

description: "Task list for Birthday Guard Bot implementation"
---

# Tasks: Birthday Guard Bot

**Input**: Design documents from `specs/001-birthday-guard-bot/`

**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/telegram-commands.md ✅, research.md ✅

**Tests**: Included — spec explicitly requests pytest tests for date calculation, leap-year cases, duplicate prevention, state transitions, and row parsing.

**Organization**: Grouped by user story (US1 → P1, US2 → P2, US3 → P3) for independent delivery.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- Each task includes an exact file path

---

## Phase 1: Setup

**Purpose**: Project initialization and full infrastructure scaffolding

- [X] T001 Create full project directory structure: `app/bot/handlers/`, `app/bot/middlewares/`, `app/bot/keyboards/`, `app/services/`, `app/repositories/`, `app/models/`, `app/core/`, `app/utils/`, `tests/` — add `__init__.py` to every package directory
- [X] T002 Initialize `pyproject.toml` with uv: project metadata, all runtime deps (`aiogram>=3`, `apscheduler`, `gspread`, `google-auth`, `pydantic-settings`, `python-dotenv`, `structlog`, `tenacity`, `aiosqlite`), dev deps (`ruff`, `mypy`, `pytest`, `pytest-asyncio`, `freezegun`), tool sections for ruff and mypy strict
- [X] T003 [P] Create `.env.example` documenting all config fields: `BOT_TOKEN`, `GROUP_CHAT_ID`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON`, `REMOVE_BEFORE_DAYS=3`, `RETURN_AFTER_DAYS=2`, `TIMEZONE=Europe/Moscow`, `CHECK_HOUR=9`, `CHECK_MINUTE=0`, `DB_PATH=data/birthday_guard.db`
- [X] T004 [P] Create `Dockerfile`: multistage build (`builder` stage installs deps with uv; `runtime` stage uses `python:3.12-slim`), non-root user `botuser`, copy app only, `HEALTHCHECK CMD python -c "import asyncio; asyncio.run(__import__('aiosqlite').connect('${DB_PATH:-data/birthday_guard.db}'))"`, `CMD ["python", "-m", "app.main"]`
- [X] T005 [P] Create `docker-compose.yml`: `bot` service using built image, `env_file: .env`, named volume `birthday_guard_data` mounted at `/app/data`, restart policy `unless-stopped`
- [X] T006 [P] Create `README.md` with: project overview, prerequisites, bot creation via @BotFather, granting admin rights, getting `chat_id`, Google Sheets API setup, creating Service Account and JSON key, sharing sheet with Service Account email, local run instructions, Docker run instructions, troubleshooting section

---

## Phase 2: Foundational

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement `app/core/config.py`: `Settings(BaseSettings)` with all fields from `.env.example`; `GOOGLE_CREDENTIALS_JSON` accepts either a file path or inline JSON string; validators for `TIMEZONE` (must be a valid pytz zone), `CHECK_HOUR` (0–23), `CHECK_MINUTE` (0–59); instantiate singleton `settings = Settings()`
- [X] T008 [P] Implement `app/core/logging.py`: `setup_logging(log_level: str)` configures structlog with JSON renderer in production and ConsoleRenderer in dev (detected via `LOG_FORMAT` env var); `get_logger(name: str)` returns bound logger; call at startup before any other imports log
- [X] T009 [P] Implement `app/utils/date_utils.py`: `days_until_birthday(birth_date: date, today: date) -> int` — ignores birth year, handles Feb 29 → Mar 1 in non-leap years, wraps correctly across year boundary; `days_since_birthday(birth_date: date, today: date) -> int` — symmetric counterpart
- [X] T010 [P] Implement `app/models/employee.py`: `Employee(BaseModel)` with fields `tg_username: str`, `full_name: str`, `birth_date: date`, `wishes: str | None`, `comment: str | None`; `@field_validator('birth_date', mode='before')` parses `dd.mm.yyyy` string, raises `ValueError` on any other format; normalize empty/whitespace `wishes`/`comment` to `None`
- [X] T011 [P] Implement `app/models/birthday_event.py`: `EventStatus(str, Enum)` with `REMOVED = "removed"` and `RESTORED = "restored"`; `BirthdayEvent(BaseModel)` matching the data-model.md schema (`id`, `username`, `birth_date`, `year`, `removed_at`, `restored_at`, `status`)
- [X] T012 Implement `app/repositories/birthday_event_repo.py`: `BirthdayEventRepository` accepting `aiosqlite.Connection`; `init_db()` runs the full SQL schema from data-model.md (table + two indexes); `get_by_username_year(username, year) -> BirthdayEvent | None`; `create_removed(username, birth_date, year, removed_at) -> BirthdayEvent` (raises `IntegrityError` on duplicate — caller must handle); `mark_restored(username, year, restored_at)` updates status + timestamp; `list_removed() -> list[BirthdayEvent]`
- [X] T013 Write `tests/conftest.py`: `@pytest_asyncio.fixture async def db()` — creates in-memory aiosqlite connection, runs `init_db()`, yields, closes; `@pytest.fixture def mock_bot()` — `MagicMock(spec=aiogram.Bot)` with async-aware method mocks; `@pytest.fixture def frozen_today(freezer)` — helper using `freezegun` for date-sensitive tests

**Checkpoint**: Foundation ready — all user story implementation can now begin

---

## Phase 3: User Story 1 — Automated Birthday Removal & Notification (Priority: P1) 🎯 MVP

**Goal**: Bot reads employees daily, removes those with birthdays in `REMOVE_BEFORE_DAYS` days, sends one combined notification per birthday date

**Independent Test**: Set one test employee's birthday to today + `REMOVE_BEFORE_DAYS` days; start bot; verify user is removed from group and one notification appears in the group chat

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementing

- [X] T014 [P] [US1] Write `tests/test_date_utils.py`: `test_days_until_birthday_standard`, `test_days_until_birthday_today`, `test_days_until_birthday_tomorrow`, `test_days_until_birthday_leap_year_feb29_nonleap_treated_as_mar1`, `test_days_until_birthday_wraps_year_boundary`, `test_days_since_birthday_standard`
- [X] T015 [P] [US1] Write `tests/test_google_sheets_service.py`: `test_parse_valid_row`, `test_parse_empty_wishes_normalized_to_none`, `test_parse_empty_comment_normalized_to_none`, `test_parse_malformed_date_returns_none`, `test_parse_missing_username_returns_none`, `test_parse_missing_full_name_returns_none`, `test_get_employees_skips_bad_rows_and_continues`
- [X] T016 [P] [US1] Write `tests/test_birthday_event_repo.py` (removal coverage): `test_create_removed_success`, `test_create_removed_duplicate_raises_integrity_error`, `test_get_by_username_year_found`, `test_get_by_username_year_not_found`, `test_list_removed_returns_only_removed_status`

### Implementation for User Story 1

- [X] T017 [US1] Implement `app/services/google_sheets_service.py`: `GoogleSheetsService` accepts `Settings`; `_build_client()` authenticates via `gspread.service_account_from_dict(json.loads(credentials_json))`; `fetch_employees() -> list[Employee]` — opens sheet by ID, gets all records, validates each row via `Employee` model, logs skipped rows with `structlog.warning(event="row_skipped", ...)`, wraps API call with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), before_sleep=log_retry)` from tenacity
- [X] T018 [US1] Implement `app/services/telegram_service.py`: `TelegramService` accepts `Bot` and `Settings`; `check_bot_is_admin() -> bool` calls `getChatAdministrators`; `get_chat_member(username: str) -> ChatMember | None`; `ban_and_unban(username: str)` — calls `banChatMember` then `unbanChatMember(only_if_banned=True)`, wrapped with tenacity retry; `send_message(text: str)` posts to `GROUP_CHAT_ID`; all methods catch `TelegramBadRequest`, `TelegramForbiddenError`, `TelegramRetryAfter` (respect `retry_after`), log each error with structlog; flood control uses `asyncio.sleep(e.retry_after)` before tenacity retry
- [X] T019 [US1] Implement `app/services/birthday_service.py`: `BirthdayService` accepts `Settings` and `date_utils` functions; `get_employees_to_remove(employees: list[Employee], today: date) -> dict[date, list[Employee]]` — groups employees by upcoming birthday date where `days_until == REMOVE_BEFORE_DAYS`; `build_notification_message(birthday_date: date, employees: list[Employee], days: int) -> str` — formats combined message per spec (🎉 header, days count, each employee's full_name @username, non-empty wishes/comment blocks only)
- [X] T020 [US1] Implement `app/services/scheduler_service.py` — removal job: `SchedulerService` accepts all services and repo; `setup(bot: Bot)` creates `AsyncIOScheduler(timezone=tz)`, adds `daily_job` with `CronTrigger(hour=CHECK_HOUR, minute=CHECK_MINUTE)`, `max_instances=1`, `misfire_grace_time=3600`, `coalesce=True`; `daily_job()`: log start, call `google_sheets.fetch_employees()`, call `birthday_service.get_employees_to_remove()`, for each employee-to-remove check `repo.get_by_username_year(username, year)` — skip if exists, else call `telegram_service.ban_and_unban()` + `repo.create_removed()` + log; group removed employees by date, call `telegram_service.send_message(build_notification_message(...))` once per date group; log job completion
- [X] T021 [US1] Implement `app/main.py`: async `main()` — `setup_logging()`, load `settings`, init aiosqlite DB, init `Bot`, `Dispatcher`, all services, `SchedulerService`; register shutdown signals (`SIGINT`, `SIGTERM`) for graceful stop (scheduler shutdown, DB close, bot session close); `dp.startup.register(on_startup)` / `dp.shutdown.register(on_shutdown)`; `asyncio.run(main())`
- [X] T022 [US1] Implement `app/bot/handlers/__init__.py` and `app/bot/keyboards/__init__.py` (stubs); register dispatcher router in `app/main.py`

**Checkpoint**: US1 independently functional — bot removes employees before their birthday and sends one combined notification per date

---

## Phase 4: User Story 2 — Automatic Post-Birthday Restoration (Priority: P2)

**Goal**: Bot auto-restores removed employees `RETURN_AFTER_DAYS` after birthday; re-removes any employee that was manually re-added during the birthday window

**Independent Test**: Insert a `status=removed` record with `year=current_year` and a birthday 3 days ago; verify bot restores the user on next scheduler run without a group notification

### Tests for User Story 2 ⚠️ Write FIRST — verify they FAIL before implementing

- [X] T023 [P] [US2] Add to `tests/test_birthday_event_repo.py`: `test_mark_restored_transitions_status`, `test_mark_restored_sets_restored_at`, `test_list_removed_excludes_restored_records`
- [X] T024 [P] [US2] Add to `tests/test_date_utils.py`: `test_days_since_birthday_zero_on_birthday`, `test_days_since_birthday_wraps_year`; add to `tests/test_birthday_service.py`: `test_get_employees_to_restore`, `test_get_employees_for_reremoval_when_manually_readded`

### Implementation for User Story 2

- [X] T025 [US2] Extend `app/services/telegram_service.py` with `restore_user(username: str)` — calls `unbanChatMember(only_if_banned=False)` to re-invite; handles `TelegramBadRequest` (user already in chat → log and skip); logs success with structlog; same tenacity retry wrapper
- [X] T026 [US2] Extend `app/services/birthday_service.py` with: `get_employees_to_restore(removed_events: list[BirthdayEvent], today: date) -> list[BirthdayEvent]` — filters where `days_since_birthday >= RETURN_AFTER_DAYS`; `get_employees_for_reremoval(employees: list[Employee], removed_events: list[BirthdayEvent], today: date) -> list[Employee]` — FR-005a: for removed events where birthday has not yet passed, intersect with provided `current_members` set (caller must supply membership check result)
- [X] T027 [US2] Extend `app/services/scheduler_service.py` `daily_job()` with: (a) re-removal block — for each `REMOVED` event where birthday not yet passed, call `telegram_service.get_chat_member(username)`; if still member → call `ban_and_unban()` + log re-removal; (b) restoration block — call `birthday_service.get_employees_to_restore()`, for each call `telegram_service.restore_user()` + `repo.mark_restored()` + log; no group notification sent

**Checkpoint**: US2 independently functional — removed employees auto-restored; manually re-added employees are re-removed on next daily run

---

## Phase 5: User Story 3 — Manual Bulk Restoration via /add_all (Priority: P3)

**Goal**: Group admin can run `/add_all` to immediately restore all bot-removed employees; non-admins are silently ignored; bot replies to admin with count

**Independent Test**: Insert two `status=removed` records; admin sends `/add_all`; verify both restored in DB and bot replies with `"Restored 2 employee(s)."`; verify non-admin `/add_all` produces no bot reply to the group

### Tests for User Story 3 ⚠️ Write FIRST — verify they FAIL before implementing

- [X] T028 [P] [US3] Write `tests/test_admin_handler.py`: `test_add_all_admin_restores_all_and_replies_count`, `test_add_all_admin_replies_nothing_to_restore_when_none_removed`, `test_add_all_non_admin_produces_no_group_reply`

### Implementation for User Story 3

- [X] T029 [US3] Implement `app/bot/middlewares/admin_check.py`: `AdminCheckMiddleware(BaseMiddleware)` — in `__call__`, for messages containing `/add_all`, call `telegram_service.get_chat_member(user.username)`; if not admin, `return` without calling `handler`; else `await handler(event, data)`
- [X] T030 [US3] Implement `app/bot/handlers/admin.py`: `add_all_router = Router()`; `@add_all_router.message(Command("add_all"))` handler — injects `BirthdayEventRepository` and `TelegramService` from middleware data; calls `repo.list_removed()`, for each calls `telegram_service.restore_user()` + `repo.mark_restored(now())`; replies to message with `f"Restored {count} employee(s)."` or `"No employees are currently removed."` (reply is visible only as a reply to the command, not a broadcast)
- [X] T031 [US3] Register in `app/main.py`: `dp.include_router(add_all_router)`; register `AdminCheckMiddleware` on the message observers; inject `repo` and `telegram_service` into handler data via middleware

**Checkpoint**: US3 independently functional — admin `/add_all` restores all removed; non-admin ignored; reply confirms count

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and final validation

- [X] T032 [P] Run full test suite: `uv run pytest tests/ -v --tb=short` — all tests must pass; fix any failures before proceeding
- [ ] T033 [P] Run MyPy strict: `uv run mypy app/ tests/ --strict` — resolve all type errors; add `py.typed` marker to `app/`
- [X] T034 [P] Run Ruff: `uv run ruff check app/ tests/ --fix` and `uv run ruff format app/ tests/` — zero lint warnings
- [ ] T035 Build Docker image and verify compose: `docker compose build && docker compose up -d` — `docker compose ps` must show `(healthy)`; `docker compose logs` must show structured JSON startup log with scheduler start event
- [ ] T036 Run quickstart.md validation checklist — manually verify each checkbox item against a running instance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001, T002) — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Foundational completion; can run in priority order P1 → P2 → P3
- **Polish (Phase N)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Can start after Phase 2 — extends `scheduler_service.py` and `telegram_service.py` already created in US1 (US1 must finish T017–T021 before T025–T027)
- **US3 (P3)**: Can start after Phase 2 — adds new handler/middleware files; requires `telegram_service.py` from US1 (T018)

### Within Each User Story

1. Tests MUST be written and FAIL before any implementation task starts
2. Models (Phase 2) before services
3. Services before handlers
4. Story complete and checkpoint validated before moving to next

### Parallel Opportunities

- All T003–T006 (Setup) can run in parallel
- T008–T011 (Foundational models + utils) can run in parallel
- T014–T016 (US1 tests) can all run in parallel
- T023–T024 (US2 tests) can run in parallel
- T032–T034 (Polish checks) can run in parallel

---

## Parallel Example: User Story 1

```text
# Run all US1 tests in parallel (they are independent files):
Task T014: tests/test_date_utils.py
Task T015: tests/test_google_sheets_service.py
Task T016: tests/test_birthday_event_repo.py (removal coverage)

# Then implement in order (each builds on previous):
Task T017: google_sheets_service.py
Task T018: telegram_service.py
Task T019: birthday_service.py
Task T020: scheduler_service.py (removal job)
Task T021: main.py
Task T022: handlers/__init__.py stubs
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: bot removes employees and sends notification correctly
5. Demo / deploy

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → removal + notification working → validate independently → demo
3. US2 → auto-restoration + re-removal guard working → validate independently → demo
4. US3 → admin /add_all working → validate independently → demo
5. Polish → all quality gates green → production-ready

---

## Notes

- **[P]** = different files, no dependencies on in-progress tasks in the same phase
- **[US#]** = traceability back to user story in spec.md
- Tests must FAIL before implementing — verify with `pytest -k test_name`
- Commit after each phase checkpoint
- `freezegun` is required for any test that depends on today's date
- `aiosqlite` in tests uses `:memory:` database — no file system side effects
- Total tasks: **36**
