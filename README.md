# Birthday Guard Bot

A production-ready Telegram bot that tracks employee birthdays from Google Sheets,
automatically removes employees from a Telegram supergroup before their birthday
(so colleagues can prepare a surprise), and restores them automatically afterward.

## Features

- Daily birthday check via configurable scheduler
- Removes employees `REMOVE_BEFORE_DAYS` days before their birthday
- Sends one combined group notification per upcoming birthday date
- Automatically restores employees `RETURN_AFTER_DAYS` after their birthday
- `/add_all` admin command for emergency bulk restoration
- Idempotent — safe to restart at any time; no duplicate actions
- Full structlog structured logging
- tenacity retry on all Telegram and Google API calls

---

## Prerequisites

- Python 3.12+ and [uv](https://github.com/astral-sh/uv)
- Docker + Docker Compose (for containerised deployment)
- A Telegram bot token
- A Telegram supergroup where the bot has admin rights
- A Google Cloud Service Account with access to a Google Sheet

---

## Setup

### 1. Create a Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newbot` and follow the prompts.
3. Copy the **API token** — this is your `BOT_TOKEN`.

### 2. Add the Bot to Your Supergroup and Grant Admin Rights

1. Add the bot as a member of your Telegram supergroup.
2. Open **Group Settings → Administrators → Add Admin**.
3. Select the bot and enable at minimum:
   - **Restrict Members** (ban/unban users)
   - **Invite Users via Link**
4. Save changes.

### 3. Get the Group Chat ID

Send any message to the group, then open:

```
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

Find the `chat.id` field in the response — it will be a negative integer (e.g. `-1001234567890`).
This is your `GROUP_CHAT_ID`.

### 4. Set Up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or use an existing one).
3. Enable the **Google Sheets API** and **Google Drive API**.

### 5. Create a Service Account

1. In the Cloud Console: **IAM & Admin → Service Accounts → Create Service Account**.
2. Give it a name (e.g. `birthday-bot`), click **Create and Continue**.
3. Skip optional role/user grant steps, click **Done**.
4. Click on the service account → **Keys → Add Key → Create new key → JSON**.
5. Download the JSON key file. This is your `GOOGLE_CREDENTIALS_JSON`.

### 6. Share the Google Sheet with the Service Account

1. Open your Google Sheet.
2. Click **Share**.
3. Paste the service account email (found in the JSON key under `client_email`).
4. Grant **Viewer** access. Click **Send**.
5. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

### 7. Prepare the Google Sheet

The sheet must have a header row followed by employee data rows:

| tg_username | full_name | birth_date | wishes | comment |
|-------------|-----------|------------|--------|---------|
| ivan_petrov | Иван Петров | 21.05.1991 | Любит кофе | Работает в QA |

- `tg_username`: Telegram username **without** the `@` prefix
- `birth_date`: strictly `dd.mm.yyyy` format
- `wishes` and `comment`: optional; leave empty if not needed

---

## Running Locally

```bash
# Clone and install
git clone <repo-url>
cd birthday-guard-bot
uv sync --extra dev

# Configure
cp .env.example .env
# Edit .env — set BOT_TOKEN, GROUP_CHAT_ID, GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON

# Run
uv run python -m app.main

# Tests
uv run pytest tests/ -v

# Type check
uv run mypy app/ tests/ --strict

# Lint
uv run ruff check app/ tests/
```

---

## Running with Docker

```bash
cp .env.example .env
# Edit .env

docker compose build
docker compose up -d

# Check status
docker compose ps       # should show "healthy"
docker compose logs -f  # structured JSON logs
```

The SQLite database is persisted in a named Docker volume (`birthday_guard_data`)
and survives container restarts.

To stop:

```bash
docker compose down
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram bot API token |
| `GROUP_CHAT_ID` | ✅ | — | Telegram supergroup chat ID (negative integer) |
| `GOOGLE_SHEET_ID` | ✅ | — | Google Sheet ID from URL |
| `GOOGLE_CREDENTIALS_JSON` | ✅ | — | Service account JSON (file path or raw JSON string) |
| `REMOVE_BEFORE_DAYS` | — | `3` | Days before birthday to remove employee |
| `RETURN_AFTER_DAYS` | — | `2` | Days after birthday to restore employee |
| `TIMEZONE` | — | `Europe/Moscow` | Scheduler timezone (pytz zone name) |
| `CHECK_HOUR` | — | `9` | Hour of daily check (0–23) |
| `CHECK_MINUTE` | — | `0` | Minute of daily check (0–59) |
| `DB_PATH` | — | `data/birthday_guard.db` | SQLite database file path |
| `LOG_FORMAT` | — | `json` | `json` or `console` |
| `LOG_LEVEL` | — | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Troubleshooting

**Bot doesn't remove users**
- Verify the bot is an admin with "Restrict Members" permission.
- Check logs for `telegram_error` events — they include the specific error type.
- Ensure `tg_username` in the sheet matches the user's current Telegram username (no `@`).

**Bot can't read the sheet**
- Confirm the sheet is shared with the service account email.
- Check logs for `sheets_error` events.
- Ensure both Google Sheets API and Google Drive API are enabled in the Cloud project.

**Duplicate notifications or actions**
- This should not happen — state is persisted in SQLite.
- If it does, check `DB_PATH` is mounted to a persistent volume in Docker.

**Flood control errors**
- The bot retries with exponential backoff and respects Telegram's `retry_after`.
- For large-scale use, consider increasing `RETURN_AFTER_DAYS` to spread actions.

**February 29 birthdays**
- In non-leap years, February 29 is treated as March 1.
