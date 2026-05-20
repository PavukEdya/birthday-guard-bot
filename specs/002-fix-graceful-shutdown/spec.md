# Feature Specification: Fix Graceful Shutdown & Scheduler Startup

**Feature Branch**: `002-fix-graceful-shutdown`

**Created**: 2026-05-20

**Status**: Draft

**Input**: User description: "нажимаю ctrl+c в консоли и получаю только {"signal": 2, "event": "shutdown_signal_received", "level": "info", "logger": "__main__", "timestamp": "..."} но не завершается работа, также нет лога о проверки данных или вообще не запускается"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bot Stops Cleanly on Ctrl+C (Priority: P1)

The developer or operator runs the bot in the terminal and presses Ctrl+C to stop it. The bot should fully terminate within a few seconds, releasing all resources (database connections, scheduler jobs, Telegram polling) and exiting the process.

**Why this priority**: Without a working shutdown, the process hangs indefinitely after a stop signal. This blocks deployments, restarts, and normal operator workflows.

**Independent Test**: Run the bot, press Ctrl+C, observe that all shutdown logs appear and the process exits with code 0 within 5 seconds.

**Acceptance Scenarios**:

1. **Given** the bot is running and polling Telegram, **When** the operator presses Ctrl+C (SIGINT), **Then** the bot logs shutdown steps (scheduler stopped, dispatcher stopped, DB closed), the process exits within 5 seconds, and the terminal prompt returns.
2. **Given** the bot is running inside Docker, **When** `docker stop` sends SIGTERM, **Then** the same clean shutdown sequence occurs and the container exits without a timeout kill.
3. **Given** a shutdown is in progress, **When** the operator presses Ctrl+C a second time, **Then** the bot performs a forced exit immediately rather than hanging.

---

### User Story 2 - Scheduler Starts and Logs Birthday Check on Boot (Priority: P1)

When the bot starts, the scheduler should initialize, register the birthday-check job, and emit a log entry confirming it is running. The first scheduled check should execute at the configured time (or immediately if overdue) and produce observable log output.

**Why this priority**: Without confirming the scheduler starts, there is no way to verify birthday notifications will ever fire. This is the core feature of the bot.

**Independent Test**: Start the bot and observe that within the first log lines there is a scheduler-started event and at least one birthday-check-triggered event (either at boot or at the configured hour).

**Acceptance Scenarios**:

1. **Given** the bot starts with valid configuration, **When** startup completes, **Then** a log entry `scheduler_started` appears, followed by a log entry `birthday_check_scheduled` indicating the next run time.
2. **Given** the scheduler is running and the configured CHECK_HOUR/CHECK_MINUTE arrives, **When** the job fires, **Then** logs show `birthday_check_started`, records fetched from Google Sheets, and `birthday_check_completed` with the count of employees evaluated.
3. **Given** Google Sheets is unreachable at check time, **When** the job fires, **Then** the error is logged, the job does not crash the scheduler, and the next run is still scheduled.

---

### User Story 3 - Startup Failure is Clearly Reported (Priority: P2)

If the bot fails to start (bad config, cannot reach Telegram, etc.), the error is logged clearly and the process exits with a non-zero code rather than silently hanging or producing no output.

**Why this priority**: Silent startup failures are difficult to diagnose. Clear error output reduces time-to-debug.

**Independent Test**: Start the bot with an invalid BOT_TOKEN and observe a clear error log and immediate process exit.

**Acceptance Scenarios**:

1. **Given** BOT_TOKEN is missing or invalid, **When** the bot starts, **Then** a log entry with level `error` and a descriptive message appears within 10 seconds, and the process exits with a non-zero code.
2. **Given** the database file cannot be created or migrated, **When** the bot starts, **Then** the error is logged and the process exits without hanging.

---

### Edge Cases

- What happens if SIGTERM arrives during a birthday-check job that is mid-execution — does the job complete or get cancelled cleanly?
- What happens if the scheduler job is still running when shutdown is requested — does the shutdown wait or force-cancel?
- What happens if the asyncio event loop is blocked by a synchronous call during shutdown, preventing cancellation?
- How does the system handle repeated SIGINT signals during the shutdown window?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The process MUST fully exit within 5 seconds after receiving SIGINT or SIGTERM, with all async tasks cancelled and resources released.
- **FR-002**: On receipt of SIGINT/SIGTERM, the system MUST log each shutdown step: signal received → scheduler stopped → dispatcher stopped → database closed → process exit.
- **FR-003**: On startup, the scheduler MUST log a `scheduler_started` event that includes the next scheduled run time for the birthday-check job.
- **FR-004**: When the birthday-check job executes, it MUST log `birthday_check_started` at the beginning and `birthday_check_completed` (with employee count) at the end.
- **FR-005**: The shutdown handler MUST cancel all pending asyncio tasks that were created by the bot, not only the main polling task.
- **FR-006**: A second SIGINT received during shutdown MUST trigger an immediate forced exit.
- **FR-007**: If the bot fails to start for any reason, it MUST log the error at level `error` and exit with a non-zero code within 10 seconds.
- **FR-008**: The scheduler MUST be stopped before the Telegram dispatcher is stopped during shutdown to prevent new jobs from firing during teardown.

### Key Entities

- **Shutdown Sequence**: An ordered set of teardown steps (scheduler → dispatcher → DB) that must complete before process exit; each step is logged individually.
- **Scheduler Job**: The birthday-check task registered with APScheduler; must produce observable start/end log entries on each execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After pressing Ctrl+C, the process exits within 5 seconds on every run (measured by wall-clock time from signal to shell prompt returning).
- **SC-002**: Every bot startup produces at least one `scheduler_started` log entry and one `birthday_check_scheduled` log entry before the first check runs.
- **SC-003**: Every birthday-check job execution produces a `birthday_check_started` and a `birthday_check_completed` (or `birthday_check_failed`) log entry — 100% of the time, not only on success.
- **SC-004**: Zero instances of the process hanging indefinitely after SIGINT/SIGTERM in normal operating conditions.

## Assumptions

- The bot is currently implemented with aiogram 3.x polling mode and APScheduler AsyncIOScheduler, as specified in the project requirements.
- The root cause is likely one or more of: missing `await` on shutdown coroutines, unhandled tasks preventing event-loop exit, or signal handlers not properly chaining cancellation.
- Scheduler logging gaps indicate either the scheduler is not starting (config/init error swallowed silently) or the log level filter is excluding scheduler events.
- The fix scope is limited to `app/main.py`, `app/core/`, and `app/services/scheduler_service.py` — no changes to business logic or data model.
- Docker healthcheck and SIGTERM handling are in scope because the same shutdown bug affects containerized deployments.
