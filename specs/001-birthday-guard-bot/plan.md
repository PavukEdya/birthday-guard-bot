# Implementation Plan: Birthday Guard Bot

**Branch**: `001-birthday-guard-bot` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-birthday-guard-bot/spec.md`

## Summary

A production-ready Telegram bot that reads employee records from Google Sheets daily, removes
employees from a Telegram supergroup before their birthday, and automatically restores them
afterward. State is persisted in SQLite to guarantee idempotency across restarts. The bot
exposes a single admin command (`/add_all`) for emergency bulk restoration.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: aiogram 3.x (Telegram), APScheduler (scheduling),
gspread (Google Sheets), pydantic-settings (config), structlog (logging),
tenacity (retries), aiosqlite (async SQLite), uv (packaging)

**Storage**: SQLite via aiosqlite — single `birthday_events` table; Google Sheets read-only
via gspread (in-memory cache, refreshed each daily run)

**Testing**: pytest + pytest-asyncio

**Target Platform**: Linux server (Docker container, single instance)

**Project Type**: Long-running async service / Telegram bot

**Performance Goals**: Process all employees and complete all due actions within 60 seconds
of scheduler fire; handle under 100 employee records per daily run

**Constraints**: Single instance only (no distributed locking needed); graceful shutdown
must flush in-flight scheduler job; Telegram flood control must be respected via tenacity
backoff; no persistent Telegram session state beyond SQLite events table

**Scale/Scope**: Under 100 employees; one Telegram supergroup; one Google Sheet

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Clean Architecture** ✅ Pass
  Gate: handlers → services → repositories → models; DI at main.py.
  Result: Structure enforces this; see Project Structure below.

- **II. Type Safety & Async-First** ✅ Pass
  Gate: Full type hints; MyPy strict; async/await throughout; no blocking I/O.
  Result: aiogram 3.x and aiosqlite are fully async; MyPy + Ruff configured in pyproject.toml.

- **III. Idempotency & Persistent State** ✅ Pass
  Gate: Every mutation guarded by SQLite state check; max_instances=1 on scheduler job.
  Result: birthday_events table with (username, year) unique constraint; FR-005 + FR-005a.

- **IV. Observability** ✅ Pass
  Gate: structlog at startup; all 8 mandatory event types logged.
  Result: structlog configured in core/logging.py; all events enumerated in requirements.

- **V. Resilience & Production Readiness** ✅ Pass
  Gate: tenacity on all external I/O; admin-rights pre-check; graceful shutdown; Docker healthcheck.
  Result: All error cases covered in FR-007/FR-008; multistage Dockerfile required.

**Post-design re-check**: No violations introduced in Phase 1 design. All entities and
contracts respect layer boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/001-birthday-guard-bot/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── telegram-commands.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
app/
├── bot/
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── admin.py          # /add_all command handler
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── admin_check.py    # admin-only middleware
│   └── keyboards/
│       └── __init__.py       # (no keyboards needed for this bot)
├── services/
│   ├── __init__.py
│   ├── birthday_service.py   # date calculation logic
│   ├── telegram_service.py   # ban/unban/check-admin operations
│   ├── google_sheets_service.py  # sheet read + cache + validation
│   └── scheduler_service.py  # APScheduler job orchestration
├── repositories/
│   ├── __init__.py
│   └── birthday_event_repo.py  # SQLite CRUD for birthday_events
├── models/
│   ├── __init__.py
│   ├── employee.py           # Pydantic model for sheet row
│   └── birthday_event.py     # Pydantic model for DB record + status enum
├── core/
│   ├── __init__.py
│   ├── config.py             # pydantic-settings Settings class
│   └── logging.py            # structlog setup
├── utils/
│   ├── __init__.py
│   └── date_utils.py         # leap-year handling, birthday distance calc
└── main.py                   # composition root, startup/shutdown

tests/
├── __init__.py
├── test_birthday_service.py  # date calculation + leap year
├── test_google_sheets_service.py  # row parsing + validation
├── test_birthday_event_repo.py    # duplicate prevention + state transitions
└── conftest.py               # fixtures (in-memory SQLite, mock bot)

Dockerfile
docker-compose.yml
pyproject.toml
.env.example
README.md
```

**Structure Decision**: Single project at repository root. Matches the structure prescribed
in CLAUDE.md and satisfies Principle I (Clean Architecture). No frontend, no separate
API service — the bot IS the service.

## Complexity Tracking

> No constitution violations. Section intentionally empty.
