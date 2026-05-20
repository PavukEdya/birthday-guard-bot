# Quickstart: Birthday Guard Bot

**Branch**: `001-birthday-guard-bot` | **Date**: 2026-05-18

---

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed (`pip install uv` or via system package manager)
- Docker + docker-compose (for containerised run)
- A Telegram bot token (from @BotFather)
- A Telegram supergroup where the bot is an admin with `ban_users` + `invite_users` rights
- A Google Service Account JSON key with read access to the target Google Sheet

---

## Local Development

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd birthday-guard-bot
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values (see .env.example for all fields)
```

Required values:

```env
BOT_TOKEN=<telegram bot token>
GROUP_CHAT_ID=<negative integer, e.g. -1001234567890>
GOOGLE_SHEET_ID=<sheet id from URL>
GOOGLE_CREDENTIALS_JSON=<path to service account JSON file, or inline JSON string>
```

### 3. Run the bot

```bash
uv run python -m app.main
```

The bot will connect to Telegram, start polling, and schedule the daily birthday check.
Logs are written to stdout in structured JSON format.

### 4. Run tests

```bash
uv run pytest tests/ -v
```

---

## Docker Run

### 1. Build and start

```bash
cp .env.example .env
# Fill in .env
docker-compose up --build
```

### 2. Check health

```bash
docker-compose ps          # should show "healthy"
docker-compose logs -f     # structured JSON logs
```

### 3. Stop

```bash
docker-compose down
```

The `birthday_events` SQLite database is persisted in a named Docker volume
(`birthday_guard_data`) and survives container restarts.

---

## Validation Checklist

After startup, verify:

- [ ] Bot logs show `"Scheduler started"` with configured timezone, hour, and minute.
- [ ] Bot responds to `/add_all` in the group (as an admin) with a count reply.
- [ ] Non-admin `/add_all` produces no visible response to the group.
- [ ] A test employee with a birthday set to today + `REMOVE_BEFORE_DAYS` days is removed
      after the scheduler fires and the group receives a notification.
- [ ] The same employee is not removed a second time when the scheduler fires again.
- [ ] After `RETURN_AFTER_DAYS` days, the employee is restored without any group message.
- [ ] A malformed row in the sheet produces a warning log but does not stop the job.
