# Data Model: Fix Graceful Shutdown & Scheduler Startup

## Scope

This fix involves no schema changes and no new entities. The `birthday_events` table and all Pydantic models remain unchanged.

## Affected State Transitions

### Shutdown Lifecycle (new ordered sequence)

```
RUNNING
  → signal received (SIGINT/SIGTERM)
  → stop_event set (via call_soon_threadsafe)
  → dp.stop_polling() called
  → polling_task awaited (aiogram finishes cleanly)
  → scheduler.shutdown(wait=False) called
  → bot.session.close() awaited
  → DB connection closed (async with block exits)
  → process exits (code 0)
```

**Previous (broken) sequence**:
```
RUNNING
  → signal received
  → stop_event set
  → asyncio.gather waits for dp.start_polling (NEVER RETURNS — deadlock)
```

### Scheduler Startup State

```
CREATED (SchedulerService.__init__)
  → start() called
  → job registered with CronTrigger
  → AsyncIOScheduler.start() called
  → next_run_time populated by APScheduler
  → scheduler_started logged WITH next_run_time
  → RUNNING (waits until CHECK_HOUR:CHECK_MINUTE)
  → _daily_job fires → daily_job_start logged
```

## No New Entities

No migrations, no new tables, no new Pydantic models required.
