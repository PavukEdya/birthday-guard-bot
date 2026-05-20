# Research: Fix Graceful Shutdown & Scheduler Startup

## Root Cause Analysis

### Bug 1 (CRITICAL): asyncio.gather Deadlock — Process Hangs on Ctrl+C

**Location**: `app/main.py:91-95`

```python
await asyncio.gather(
    dp.start_polling(bot, handle_signals=False),
    stop_event.wait(),
)
# finally block here: dp.stop_polling() is never reached
```

**Decision**: Replace with explicit task + sequential teardown.

**Rationale**: `asyncio.gather` waits for ALL coroutines. When `stop_event.wait()` completes after a signal, `gather` still blocks waiting for `dp.start_polling`. `dp.start_polling` only returns when `dp.stop_polling()` is called — but that call is in the `finally` block which can only run after `gather` returns. Classic deadlock.

**Fix**:
```python
polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
await stop_event.wait()
await dp.stop_polling()   # breaks the polling loop
await polling_task         # waits for clean exit
```

**Alternatives considered**:
- `asyncio.wait(tasks, return_when=FIRST_COMPLETED)` + manual cancellation — more verbose, same result
- `dp.start_polling(..., handle_signals=True)` — surrenders signal control to aiogram, loses structured teardown order

---

### Bug 2 (HIGH): APScheduler Blocking Shutdown

**Location**: `app/services/scheduler_service.py:59-61`

```python
async def shutdown(self) -> None:
    self._scheduler.shutdown(wait=True)  # synchronous blocking call in async context
```

**Decision**: Change to `wait=False`.

**Rationale**: `AsyncIOScheduler.shutdown(wait=True)` blocks the calling thread until all running jobs finish. Inside an `async` function this blocks the event loop, preventing all other async tasks (including the aiogram teardown) from progressing. Since we control teardown order (scheduler is shut down before bot), `wait=False` is safe — no new jobs will fire because the scheduler is being stopped.

**Alternatives considered**:
- `loop.run_in_executor(None, lambda: scheduler.shutdown(wait=True))` — runs sync shutdown in a thread; overkill when `wait=False` is sufficient
- Keeping `wait=True` but running before `await polling_task` — still blocks event loop

---

### Bug 3 (MEDIUM): Signal Handler Calls asyncio.Event.set() Unsafely

**Location**: `app/main.py:80-86`

```python
def _handle_signal(sig: int, _: object) -> None:
    logger.info("shutdown_signal_received", signal=sig)
    stop_event.set()  # asyncio.Event is not thread-safe
```

**Decision**: Use `loop.call_soon_threadsafe(stop_event.set)`.

**Rationale**: `signal.signal()` handlers run at the C level and may interrupt asyncio's internal state. `asyncio.Event.set()` modifies internal state and is not documented as thread-safe. `call_soon_threadsafe` schedules the callback in the event loop's thread-safe queue, ensuring correct ordering.

Note: On Windows `loop.add_signal_handler()` (the preferred asyncio method) is NOT available. Using `signal.signal()` with `call_soon_threadsafe` is the correct cross-platform approach.

---

### Bug 4 (LOW): No next_run_time in scheduler_started Log

**Location**: `app/services/scheduler_service.py:52-57`

**Decision**: Log `next_run_time` from the job after `scheduler.start()`.

**Rationale**: APScheduler populates `job.next_run_time` only after `scheduler.start()` is called. Logging this value tells operators exactly when the first check will fire, preventing confusion when no birthday-check logs appear immediately.

**Fix**:
```python
self._scheduler.start()
job = self._scheduler.get_job("daily_birthday_check")
next_run = str(job.next_run_time) if job else "unknown"
logger.info("scheduler_started", ..., next_run=next_run)
```

---

### Non-Bug: Scheduler Not Running Daily Check Immediately

**Observation**: The `_daily_job` only fires at the configured `CHECK_HOUR:CHECK_MINUTE`. After start, there are no `daily_job_start` logs until that time.

**Decision**: No code change needed; document in quickstart.

**Rationale**: This is by design. CronTrigger fires at the configured time, not on startup. Adding `next_run_time` logging (Bug 4 fix) will make this clear to operators.

---

## Dependency Versions Confirmed (no changes needed)

- `apscheduler>=3.10` — `AsyncIOScheduler` is the correct class
- `aiogram>=3.0` — `dp.stop_polling()` is the documented stop method
- `asyncio` stdlib — `call_soon_threadsafe` available since Python 3.4
