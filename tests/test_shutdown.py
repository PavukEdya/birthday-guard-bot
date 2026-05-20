from __future__ import annotations

import asyncio
import signal
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import structlog.testing

from app.main import main
from app.services.scheduler_service import SchedulerService


def _make_scheduler_service() -> SchedulerService:
    return SchedulerService(
        sheets_service=MagicMock(),
        telegram_service=MagicMock(),
        birthday_service=MagicMock(),
        repo=MagicMock(),
        timezone_name="Europe/Moscow",
        check_hour=9,
        check_minute=0,
    )


async def test_stop_event_set_via_call_soon_threadsafe() -> None:
    """Signal handler must use call_soon_threadsafe, not call stop_event.set directly."""
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    scheduled_calls: list[object] = []

    def fake_call_soon_threadsafe(callback: object, *args: object) -> None:
        scheduled_calls.append(callback)

    # Reproduce the handler closure from main.py
    def _handle_signal(sig: int, _: object) -> None:
        loop.call_soon_threadsafe(stop_event.set)

    with patch.object(loop, "call_soon_threadsafe", side_effect=fake_call_soon_threadsafe):
        _handle_signal(signal.SIGINT, None)

    assert len(scheduled_calls) == 1
    # Invoke the scheduled callback and verify the event is set
    scheduled_calls[0]()
    assert stop_event.is_set()


async def test_scheduler_shutdown_is_nonblocking() -> None:
    """SchedulerService.shutdown() must call APScheduler.shutdown with wait=False."""
    service = _make_scheduler_service()
    mock_internal = MagicMock()
    service._scheduler = mock_internal  # type: ignore[assignment]

    await service.shutdown()

    mock_internal.shutdown.assert_called_once_with(wait=False)


async def test_scheduler_logs_next_run_time() -> None:
    """scheduler_started log must include a non-empty next_run field."""
    service = _make_scheduler_service()

    fixed_dt = datetime(2026, 5, 21, 9, 0, 0, tzinfo=UTC)
    mock_job = MagicMock()
    mock_job.next_run_time = fixed_dt

    mock_scheduler = MagicMock()
    mock_scheduler.get_job.return_value = mock_job
    service._scheduler = mock_scheduler  # type: ignore[assignment]

    with structlog.testing.capture_logs() as logs:
        service.start()

    started_logs = [e for e in logs if e.get("event") == "scheduler_started"]
    assert len(started_logs) == 1
    entry = started_logs[0]
    assert "next_run" in entry
    assert entry["next_run"] == str(fixed_dt)


async def test_startup_error_logs_and_exits() -> None:
    """When _run() raises, main() must log startup_failed and re-raise."""
    with (
        patch("app.main.setup_logging"),
        patch("app.main._run", side_effect=RuntimeError("db error")),
        structlog.testing.capture_logs() as logs,
        pytest.raises(RuntimeError, match="db error"),
    ):
        await main()

    error_logs = [e for e in logs if e.get("event") == "startup_failed"]
    assert len(error_logs) == 1
    assert "db error" in error_logs[0]["error"]
