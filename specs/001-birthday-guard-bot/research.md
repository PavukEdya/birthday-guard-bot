# Research: Birthday Guard Bot

**Branch**: `001-birthday-guard-bot` | **Date**: 2026-05-18

All technology choices are prescribed in CLAUDE.md. This document records the rationale
and key design decisions resolved during planning.

---

## Decision 1: Async SQLite driver (aiosqlite)

**Decision**: Use `aiosqlite` as the async wrapper around Python's built-in `sqlite3`.

**Rationale**: aiogram 3.x and APScheduler AsyncIOScheduler both run on the asyncio event
loop. Any blocking DB call would stall the loop. aiosqlite wraps sqlite3 in a background
thread and exposes an async interface, giving non-blocking behaviour without introducing
a heavier DB server.

**Alternatives considered**:
- `tortoise-orm` with SQLite backend — heavier ORM, unnecessary for a single-table schema.
- `SQLAlchemy async` — well-supported but significantly more setup for a simple use case.
- Raw `sqlite3` (sync) — would block the event loop; incompatible with async architecture.

---

## Decision 2: "Kick without permanent ban" via banChatMember + unbanChatMember

**Decision**: Remove a user by calling `banChatMember` then immediately `unbanChatMember
(only_if_banned=True)`. This evicts the user without adding them to the permanent ban list,
so they can be re-invited later.

**Rationale**: Telegram does not have a dedicated "kick" API that also allows future
re-invitation. Calling ban then immediately unban is the standard pattern for a temporary
kick. The user loses their membership but is not permanently blocked.

**Alternatives considered**:
- `kickChatMember` (deprecated Bot API method) — removed in newer API versions; not
  available in aiogram 3.x.
- Using invite links — cannot be scoped per-user without generating individual links;
  does not remove the user from the group.

---

## Decision 3: APScheduler job idempotency via misfire_grace_time + max_instances

**Decision**: Configure the daily job with `max_instances=1` and a `misfire_grace_time`
of at least 1 hour.

**Rationale**: `max_instances=1` prevents the job from running in parallel if a previous
run is still executing (e.g., slow Google Sheets response). `misfire_grace_time` ensures
that if the bot was down at the scheduled time it catches up immediately on restart rather
than skipping the run — important for correctness when birthday windows are narrow.

**Alternatives considered**:
- Distributed lock in SQLite — unnecessary for a single-instance deployment.
- Skipping misfired jobs — would cause missed birthday actions if the container restarted
  during the scheduled window.

---

## Decision 4: Google Sheets caching strategy

**Decision**: Refresh the full sheet on every daily scheduler run (no TTL cache between
runs). Within a single run, hold the fetched data in memory.

**Rationale**: The sheet is read once per day. Caching between runs adds complexity and
risks serving stale data if HR updates the sheet mid-day. At under 100 rows, a full
re-fetch takes well under 1 second and is free of consistency concerns.

**Alternatives considered**:
- TTL cache (e.g., 6-hour refresh) — adds invalidation complexity with no real benefit
  at this scale.
- Webhook-driven cache invalidation from Google — requires a public HTTPS endpoint and
  significantly more infrastructure.

---

## Decision 5: February 29 birthday handling

**Decision**: Treat February 29 birthdays as March 1 in non-leap years.

**Rationale**: This is the most common convention and avoids skipping the birthday
entirely. The distance calculation compares only month and day against the current year's
calendar, substituting (3, 1) for (2, 29) when the current year is not a leap year.

**Alternatives considered**:
- February 28 — less intuitive; the person has already "passed" their birth date
  by the time notification would fire.
- Skip the employee that year — worst outcome; the employee gets no birthday treatment.

---

## Decision 6: Notification grouping for same-day birthdays

**Decision**: When multiple employees share the same upcoming birthday date (within the
`REMOVE_BEFORE_DAYS` window), emit a single combined Telegram message listing all of them.

**Rationale**: Reduces notification noise in the group chat. A single message is also
atomic from the reader's perspective — one glance covers all upcoming birthdays.

**Alternatives considered**:
- One message per employee — generates spam for groups where several employees share
  a birthday.

---

## Decision 7: Re-removal on manual re-add (FR-005a)

**Decision**: On each daily run, for every employee whose `status = removed` and whose
birthday has not yet passed, check current Telegram group membership. If the employee
is detected as a member again, re-execute the removal.

**Rationale**: Prevents an admin from accidentally bypassing the birthday surprise by
manually re-adding the employee. The check adds one `getChatMember` API call per
still-removed employee per day — negligible at this scale.

**Alternatives considered**:
- Ignore manual re-adds — trivially bypassable; undermines the core feature.
- Require explicit admin override command — more complex UX; the bot should self-heal.
