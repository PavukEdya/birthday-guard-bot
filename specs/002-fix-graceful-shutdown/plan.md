# Implementation Plan: Fix Graceful Shutdown & Scheduler Startup

**Branch**: `002-fix-graceful-shutdown` | **Date**: 2026-05-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-fix-graceful-shutdown/spec.md`

## Summary

The bot hangs indefinitely on Ctrl+C and provides no log of when the next birthday check will run. Root cause is a deadlock in `app/main.py` where `asyncio.gather` waits for `dp.start_polling` which never exits until `dp.stop_polling()` is called — but that call is trapped in the `finally` block behind the blocked `gather`. Secondary issues: `scheduler.shutdown(wait=True)` blocks the event loop, and the signal handler calls `asyncio.Event.set()` without `call_soon_threadsafe`. Fix requires changes to two files only: `app/main.py` and `app/services/scheduler_service.py`.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: aiogram 3.x, APScheduler 3.x (AsyncIOScheduler), structlog

**Storage**: SQLite via aiosqlite — no changes

**Testing**: pytest + pytest-asyncio — new tests for shutdown signal path

**Target Platform**: Linux server (Docker), Windows (dev machine)

**Project Type**: Long-running async service (Telegram bot daemon)

**Performance Goals**: Process exits within 5 seconds of SIGINT/SIGTERM

**Constraints**: Signal handling must work on both Windows (signal.signal) and Linux; `loop.add_signal_handler` is NOT available on Windows — `signal.signal` + `call_soon_threadsafe` is the correct cross-platform approach

**Scale/Scope**: 2 files changed, ~20 lines net

## Constitution Check

### I. Clean Architecture — PASS

Changes are confined to `main.py` (composition root) and `scheduler_service.py` (service layer). No cross-layer imports introduced.

### II. Type Safety & Async-First — PASS (fix required)

`scheduler.shutdown(wait=True)` was a blocking call in async context — fix removes the block. All changed code retains full type annotations and async/await.

### III. Idempotency & Persistent State — PASS

No changes to business logic, state checks, or DB operations.

### IV. Observability — PASS (improved)

`scheduler_started` log gains `next_run` field. Shutdown sequence gains per-step log entries.

### V. Resilience & Production Readiness — PASS (fix required)

Constitution: "The application MUST support graceful shutdown: pending scheduler jobs finish, bot polling stops cleanly, DB connections close." Current code violates this. Fix restores compliance.

**Gate status**: PASS after implementing the fix.

## Project Structure

### Documentation (this feature)

```text
specs/002-fix-graceful-shutdown/
├── plan.md              # This file
├── research.md          # Root cause analysis
├── data-model.md        # Shutdown state transitions
├── quickstart.md        # Verification guide
└── tasks.md             # Task list (/speckit-tasks output)
```

### Source Code (changes only)

```text
app/
├── main.py                           # CHANGED: shutdown logic
└── services/
    └── scheduler_service.py          # CHANGED: shutdown + startup log

tests/
└── test_shutdown.py                  # NEW: signal handling tests
```

**Structure Decision**: Single project. Only two source files change; one new test file is added. No new directories or modules needed.

## Implementation Design

### Change 1: app/main.py — Replace asyncio.gather with task pattern

**Current (broken)**:

```python
stop_event = asyncio.Event()

def _handle_signal(sig: int, _: object) -> None:
    logger.info("shutdown_signal_received", signal=sig)
    stop_event.set()               # not thread-safe

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _handle_signal)

scheduler.start()
logger.info("bot_started")

try:
    await asyncio.gather(
        dp.start_polling(bot, handle_signals=False),
        stop_event.wait(),
    )
finally:
    await dp.stop_polling()        # UNREACHABLE — gather deadlocks
    await scheduler.shutdown()
    await bot.session.close()
    logger.info("bot_stopped")
```

**Fixed**:

```python
stop_event = asyncio.Event()
loop = asyncio.get_event_loop()

def _handle_signal(sig: int, _: object) -> None:
    logger.info("shutdown_signal_received", signal=sig)
    loop.call_soon_threadsafe(stop_event.set)   # thread-safe

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _handle_signal)

scheduler.start()
logger.info("bot_started")

polling_task = asyncio.create_task(
    dp.start_polling(bot, handle_signals=False)
)
try:
    await stop_event.wait()
finally:
    logger.info("shutdown_started")
    await dp.stop_polling()                     # unblocks polling_task
    await polling_task                          # waits for clean aiogram exit
    await scheduler.shutdown()                  # non-blocking (wait=False)
    await bot.session.close()
    logger.info("bot_stopped")
```

### Change 2: app/services/scheduler_service.py — Two fixes

**Fix 2a**: `shutdown` — non-blocking:

```python
async def shutdown(self) -> None:
    self._scheduler.shutdown(wait=False)    # was wait=True — blocked event loop
    logger.info("scheduler_stopped")
```

**Fix 2b**: `start` — log next_run_time:

```python
def start(self) -> None:
    self._scheduler.add_job(...)
    self._scheduler.start()
    job = self._scheduler.get_job("daily_birthday_check")
    next_run = str(job.next_run_time) if job else "unknown"
    logger.info(
        "scheduler_started",
        timezone=str(self._tz),
        hour=self._check_hour,
        minute=self._check_minute,
        next_run=next_run,
    )
```

### Change 3: tests/test_shutdown.py — New tests

- `test_stop_event_set_via_call_soon_threadsafe` — mock the loop, fire signal handler, verify `call_soon_threadsafe` is called with `stop_event.set`
- `test_scheduler_logs_next_run_time` — start scheduler in asyncio test, capture structlog output, assert `next_run` key present
- `test_scheduler_shutdown_is_nonblocking` — mock `_scheduler.shutdown`, call `SchedulerService.shutdown()`, assert `wait=False` was passed
