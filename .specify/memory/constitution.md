<!--
Sync Impact Report
==================
Version change: [template] → 1.0.0 (initial constitution — all placeholders filled)
Modified principles: none (first ratification)
Added sections:
  - Core Principles (5 principles)
  - Technology Stack
  - Development Workflow
  - Governance
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md  ✅ Constitution Check section references updated principles
  - .specify/templates/spec-template.md  ✅ Requirements section aligns with FR/SC format
  - .specify/templates/tasks-template.md ✅ Task categories match principle-driven types
Follow-up TODOs: none — all placeholders resolved
-->

# Birthday Guard Bot Constitution

## Core Principles

### I. Clean Architecture (NON-NEGOTIABLE)

The project MUST follow a lightweight service architecture with strict layer separation:
- `app/models/` — pure Pydantic domain models, no business logic
- `app/repositories/` — data access only (SQLite via aiosqlite), no service calls
- `app/services/` — business logic only; MUST NOT import from `bot/` layer
- `app/bot/handlers/` — Telegram event handlers that delegate to services immediately
- `app/core/` — configuration and logging setup only

Dependencies flow inward: handlers → services → repositories → models.
Cross-layer imports in the wrong direction are a hard violation.
Dependency injection MUST be used at composition root (`main.py`); no service instantiation inside handlers.

### II. Type Safety & Async-First (NON-NEGOTIABLE)

All code MUST carry full type annotations — function signatures, class attributes, variables where inference is non-obvious.
`async/await` MUST be used throughout; no blocking I/O calls in the event loop.
MyPy strict mode and Ruff MUST pass with zero errors before any merge.
Global mutable state is forbidden; pass dependencies explicitly.
Hardcoded values (tokens, IDs, magic numbers) are forbidden; all config comes from `.env` via `pydantic-settings`.

### III. Idempotency & Persistent State (NON-NEGOTIABLE)

Every mutation (remove user, restore user, notify group) MUST be guarded by a state check against the `birthday_events` SQLite table.
The system MUST NOT:
- remove a user who is already removed for the current birth year
- restore a user who is already restored
- send a duplicate notification for the same event

All scheduler jobs MUST be safe to re-run after restart — they query state first, then act.
APScheduler MUST use `misfire_grace_time` and `max_instances=1` per job to prevent parallel execution.

### IV. Observability (MUST)

`structlog` MUST be configured at startup in `app/core/logging.py` and used everywhere — never `print()` or bare `logging`.
The following events MUST be logged at the appropriate level with structured context:
- Scheduler job start / finish / skip
- User removal and restoration (with username and birth year)
- Notification sent
- Telegram API errors (with error type, username, chat_id)
- Google Sheets errors (with row index, field, reason)
- Skipped / invalid rows from Google Sheets
- Tenacity retry attempts (attempt number, exception)

### V. Resilience & Production Readiness (MUST)

All external I/O (Telegram API, Google Sheets API) MUST be wrapped with `tenacity` retry logic with exponential backoff.
Before any ban/unban action the bot MUST verify it has `can_restrict_members` and `can_invite_users` admin rights.
All Telegram error cases MUST be handled explicitly: user not found, user never joined, flood control (respect `retry_after`), invalid username, bot has no rights.
Google Sheets rows that fail validation MUST be skipped with a warning log; the job MUST continue processing remaining rows.
The application MUST support graceful shutdown: pending scheduler jobs finish, bot polling stops cleanly, DB connections close.
Docker image MUST use a non-root user, multistage build, and include a `HEALTHCHECK`.

## Technology Stack

- **Runtime**: Python 3.12+
- **Telegram**: aiogram 3.x (polling mode)
- **Scheduler**: APScheduler `AsyncIOScheduler`
- **Google Sheets**: gspread + Google Service Account credentials
- **Config**: pydantic-settings + python-dotenv
- **Database**: SQLite via aiosqlite (schema: `birthday_events` table)
- **Logging**: structlog
- **Retry**: tenacity
- **Packaging**: uv (`pyproject.toml`)
- **Linting/Formatting**: Ruff
- **Type checking**: MyPy
- **Containerisation**: Docker + docker-compose
- **Testing**: pytest + pytest-asyncio

Deprecated or alternative libraries that duplicate the above are NOT permitted.

## Development Workflow

- All features start with a spec; no implementation without a clear requirement.
- Tests MUST cover: birthday date calculation, leap-year cases, duplicate-prevention logic, state transitions, Google Sheets row parsing.
- Tests are written in `tests/` using pytest; run via `uv run pytest`.
- Ruff and MyPy gates run before any commit.
- Every scheduler job MUST have a corresponding unit/integration test verifying idempotency.
- `.env.example` MUST be kept in sync with every new config field added.
- Docker build MUST succeed and `docker-compose up` MUST reach a healthy state before a feature is considered complete.

## Governance

This constitution supersedes all other practices and conventions in the repository.
Amendments require:
1. A written rationale for the change.
2. Version bump per semantic versioning (MAJOR: principle removal/redefinition; MINOR: new principle or section; PATCH: wording/clarification).
3. Propagation check across all `.specify/templates/` files.

All code reviews MUST verify compliance with Principles I–V.
Complexity beyond what the requirements demand MUST be explicitly justified in the PR description.
Use `CLAUDE.md` for runtime agent guidance; this constitution governs architectural decisions.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
