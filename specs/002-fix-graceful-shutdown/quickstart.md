# Quickstart: Verifying the Graceful Shutdown Fix

## How to Verify the Fix

### 1. Verify Clean Shutdown

Start the bot normally:
```bash
uv run python -m app.main
```

Expected logs on startup:
```json
{"event": "scheduler_started", "next_run": "2026-05-21 09:00:00+03:00", ...}
{"event": "bot_started", ...}
```

Press Ctrl+C. Expected shutdown sequence (within 5 seconds):
```json
{"event": "shutdown_signal_received", "signal": 2, ...}
{"event": "scheduler_stopped", ...}
{"event": "bot_stopped", ...}
```

The shell prompt must return. If it hangs, the fix is incomplete.

### 2. Verify Scheduler Start Log

Look for `scheduler_started` event with a `next_run` field:
```json
{
  "event": "scheduler_started",
  "timezone": "Europe/Moscow",
  "hour": 9,
  "minute": 0,
  "next_run": "2026-05-21 09:00:00+03:00",
  ...
}
```

The `next_run` field tells you exactly when the first birthday check will run. No birthday-check logs will appear until that time — this is expected.

### 3. Verify Docker Shutdown

```bash
docker-compose up -d
docker stop birthday-guard-bot
```

The container should exit within 5 seconds (before Docker's 10-second SIGKILL timeout). If it takes exactly 10 seconds and exits with code 137, the SIGTERM is not being handled.

### 4. Trigger a Manual Check (Debug)

If you need to verify the birthday check runs correctly without waiting for the scheduled time, temporarily change `CHECK_HOUR` and `CHECK_MINUTE` in `.env` to 1-2 minutes from now:
```env
CHECK_HOUR=9
CHECK_MINUTE=5   # 5 minutes from now
```

Then watch for:
```json
{"event": "daily_job_start", "date": "2026-05-20", ...}
{"event": "daily_job_complete", "date": "2026-05-20", ...}
```

## Changed Files

| File | Change |
|------|--------|
| `app/main.py` | Replace `asyncio.gather` with task+event pattern; use `call_soon_threadsafe` |
| `app/services/scheduler_service.py` | `shutdown(wait=False)`; log `next_run_time` |
