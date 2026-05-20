# Tasks: Fix Graceful Shutdown & Scheduler Startup

**Input**: Design documents from `specs/002-fix-graceful-shutdown/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Included — spec FR requirements and constitution Principle IV mandate pytest coverage for signal handling, scheduler startup, and shutdown paths.

**Organization**: Tasks grouped by user story. US1 (shutdown deadlock) and US2 (scheduler fix) are both P1; US3 (startup errors) is P2. US1 and US2 touch different files and can be implemented in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new test file that all test tasks across US1, US2, and US3 will write into.

- [x] T001 Create tests/test_shutdown.py with module docstring, imports (asyncio, signal, unittest.mock, pytest, pytest_asyncio), and empty test stubs with `pass` bodies for: `test_stop_event_set_via_call_soon_threadsafe`, `test_scheduler_shutdown_is_nonblocking`, `test_scheduler_logs_next_run_time`

**Checkpoint**: `tests/test_shutdown.py` exists and `uv run pytest tests/test_shutdown.py` collects 3 tests (all pass trivially with `pass` bodies)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No new shared infrastructure is needed — no models, schema, or configuration changes. The two bug-fix targets (`app/main.py` and `app/services/scheduler_service.py`) are independent of each other. Proceed directly to user story phases.

**⚠️ CRITICAL**: T001 (Phase 1) must complete before any test tasks in US1/US2/US3 phases.

---

## Phase 3: User Story 1 — Bot Stops Cleanly on Ctrl+C (Priority: P1) 🎯 MVP

**Goal**: Pressing Ctrl+C causes the process to fully exit within 5 seconds with structured teardown logs.

**Independent Test**: Run `uv run python -m app.main` (with valid `.env`), press Ctrl+C, verify the shell prompt returns within 5 seconds and logs show `shutdown_signal_received` → `shutdown_started` → `scheduler_stopped` → `bot_stopped`.

### Implementation for User Story 1

- [x] T002 [US1] In `app/main.py` function `main()`: (1) capture `loop = asyncio.get_event_loop()` before signal registration; (2) change `_handle_signal` body to call `loop.call_soon_threadsafe(stop_event.set)` instead of `stop_event.set()`; (3) replace the entire `asyncio.gather(dp.start_polling(...), stop_event.wait())` try/finally block with: `polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))`, then `try: await stop_event.wait()`, then `finally: logger.info("shutdown_started") / await dp.stop_polling() / await polling_task / await scheduler.shutdown() / await bot.session.close() / logger.info("bot_stopped")` — see plan.md Change 1 for exact code

### Tests for User Story 1

- [x] T003 [P] [US1] In `tests/test_shutdown.py`, implement `test_stop_event_set_via_call_soon_threadsafe`: create a `MagicMock` for the event loop, create an `asyncio.Event`, simulate calling `_handle_signal` with `signal.SIGINT` in a context where the loop mock is injected, and assert `loop.call_soon_threadsafe` was called with `stop_event.set`

**Checkpoint**: `uv run pytest tests/test_shutdown.py::test_stop_event_set_via_call_soon_threadsafe -v` passes. Manual test: bot exits cleanly within 5 seconds on Ctrl+C.

---

## Phase 4: User Story 2 — Scheduler Starts and Logs Birthday Check (Priority: P1)

**Goal**: `scheduler_started` log includes a `next_run` field; `shutdown()` does not block the event loop.

**Independent Test**: Start the bot and verify the first `scheduler_started` log line contains a `next_run` key with a parseable datetime. Verify `uv run pytest tests/test_shutdown.py::test_scheduler_shutdown_is_nonblocking` and `test_scheduler_logs_next_run_time` both pass.

### Implementation for User Story 2

- [x] T004 [P] [US2] In `app/services/scheduler_service.py` method `shutdown()`: change `self._scheduler.shutdown(wait=True)` to `self._scheduler.shutdown(wait=False)` — see plan.md Fix 2a

- [x] T005 [P] [US2] In `app/services/scheduler_service.py` method `start()`: after `self._scheduler.start()`, add `job = self._scheduler.get_job("daily_birthday_check")` and `next_run = str(job.next_run_time) if job else "unknown"`, then update the `logger.info("scheduler_started", ...)` call to include `next_run=next_run` as an additional keyword argument — see plan.md Fix 2b

### Tests for User Story 2

- [x] T006 [P] [US2] In `tests/test_shutdown.py`, implement `test_scheduler_shutdown_is_nonblocking`: construct a `SchedulerService` with all dependencies mocked (use `MagicMock` / `AsyncMock`), mock `_scheduler.shutdown`, call `await service.shutdown()`, and assert `_scheduler.shutdown` was called with `wait=False` (not `wait=True`)

- [x] T007 [P] [US2] In `tests/test_shutdown.py`, implement `test_scheduler_logs_next_run_time`: construct a `SchedulerService` with mocked dependencies, mock `_scheduler.get_job` to return a mock job with a `next_run_time` attribute set to a fixed `datetime`, call `service.start()`, and assert the structlog output (captured via `structlog.testing.capture_logs()`) contains an entry with `event == "scheduler_started"` and a non-empty `next_run` key

**Checkpoint**: `uv run pytest tests/test_shutdown.py -v` — all 4 tests pass. Bot startup log contains `next_run` field.

---

## Phase 5: User Story 3 — Startup Failure is Clearly Reported (Priority: P2)

**Goal**: If the bot cannot start (bad token, DB error), a structured error log appears and the process exits with a non-zero code.

**Independent Test**: Set `BOT_TOKEN=invalid` in `.env`, run `uv run python -m app.main`, confirm an `error`-level log appears and the process exits within 10 seconds.

### Implementation for User Story 3

- [x] T008 [US3] In `app/main.py`, wrap the body of `async def main()` in a top-level `try/except Exception as exc:` that logs `logger.error("startup_failed", error=str(exc), exc_info=True)` and re-raises (so `asyncio.run` propagates the exit code). Ensure this wraps the entire `async with aiosqlite.connect(...)` block. The `if __name__ == "__main__":` block should catch `SystemExit` and `KeyboardInterrupt` to exit cleanly without a traceback.

### Tests for User Story 3

- [x] T009 [P] [US3] In `tests/test_shutdown.py`, implement `test_startup_error_logs_and_exits`: mock `aiosqlite.connect` to raise `RuntimeError("db error")`, call `asyncio.run(main())` inside a `pytest.raises(RuntimeError)` context, and assert structlog captured an `error`-level event with key `startup_failed`

**Checkpoint**: `uv run pytest tests/test_shutdown.py -v` — all 5 tests pass. Bad-config startup produces `startup_failed` log and non-zero exit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup across all three user stories.

- [x] T010 Run full test suite `uv run pytest -v` and confirm zero regressions in existing tests (test_date_utils, test_birthday_service, test_google_sheets_service, test_birthday_event_repo, test_admin_handler)
- [x] T011 [P] Run `uv run ruff check app/main.py app/services/scheduler_service.py tests/test_shutdown.py` and fix any lint errors
- [x] T012 [P] Run `uv run mypy app/main.py app/services/scheduler_service.py` and fix any type errors
- [ ] T013 Manual verification per `specs/002-fix-graceful-shutdown/quickstart.md`: start bot with valid `.env`, press Ctrl+C, confirm process exits within 5 seconds with all expected log entries in order

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Not needed for this fix; proceed to user stories after Phase 1
- **Phase 3 (US1)**: Requires T001 complete for test tasks
- **Phase 4 (US2)**: Requires T001 complete for test tasks; can run in parallel with Phase 3 (different files)
- **Phase 5 (US3)**: Requires T001 complete and ideally T002 done (wraps `main()`)
- **Phase 6 (Polish)**: Requires all story phases complete

### User Story Dependencies

- **US1 (P1)**: Independent — only touches `app/main.py`
- **US2 (P1)**: Independent — only touches `app/services/scheduler_service.py`
- **US3 (P2)**: Builds on US1 changes in `app/main.py` (wraps same function body)

### Within Each User Story

- Implementation task before test task (tests verify the fix, not drive it TDD-style)
- Both implementation subtasks within US2 (T004, T005) touch same file — do in one editing pass

---

## Parallel Opportunities

### US1 and US2 can run in parallel (different files)

```
After T001:
  Worker A: T002 (app/main.py) → T003 (tests/test_shutdown.py)
  Worker B: T004 + T005 (app/services/scheduler_service.py) → T006 + T007 (tests/)
```

### Within US2

```
T004 and T005 are in the same file — do sequentially in one pass
T006 and T007 are separate test functions — can be written in parallel by separate agents
```

### Polish phase

```
T011 (ruff) and T012 (mypy) can run in parallel — different tools, same files
```

---

## Implementation Strategy

### MVP First (US1 + US2 — the P1 bugs)

1. Complete T001 (create test file)
2. Implement T002 (fix `app/main.py` shutdown) + T004 + T005 (fix `app/services/scheduler_service.py`) in parallel
3. Write T003, T006, T007 tests
4. **STOP and VALIDATE**: `uv run pytest tests/test_shutdown.py -v` all pass; manual Ctrl+C test succeeds
5. US3 (startup error handling) is P2 — deliver separately

### Incremental Delivery

1. T001 → T002 + T004/T005 in parallel → verify shutdown fix → ship US1+US2
2. T008 + T009 → verify startup error fix → ship US3
3. T010-T013 → polish → final ship

---

## Notes

- T004 and T005 are marked [P] because they touch different methods, but since they're in the same file they should be done in a single editing pass
- T002 is the most impactful change — the `asyncio.gather` deadlock is the direct cause of the hang
- `structlog.testing.capture_logs()` is the correct utility for asserting log output in pytest — no need to mock the logger
- All changes are confined to `app/main.py`, `app/services/scheduler_service.py`, and `tests/test_shutdown.py` — no other files touched
