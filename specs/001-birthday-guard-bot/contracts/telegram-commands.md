# Contract: Telegram Bot Interface

**Branch**: `001-birthday-guard-bot` | **Date**: 2026-05-18

The bot exposes one user-facing command and one scheduled behaviour.

---

## Commands

### /add_all

**Access**: Telegram group administrators only (verified via `getChatMember` before execution).

**Trigger**: Any group administrator sends `/add_all` in the Telegram group.

**Behaviour**:
1. Bot checks caller is an administrator of the group. If not → silently ignore or reply
   with a permission error visible only to the caller (ephemeral reply).
2. Bot queries `birthday_events` for all records with `status = 'removed'`.
3. For each record, bot calls `unbanChatMember` (re-invite) and marks the record
   `status = 'restored'`.
4. Bot replies to the command message with a count: e.g. `"Restored 3 employee(s)."` or
   `"No employees are currently removed."` No group-wide broadcast.

**Error responses**:
- Bot not admin → log error, reply to caller: `"Bot lacks admin rights to restore members."`
- Telegram flood control → retry with backoff; if ultimately fails, log and reply to caller.

---

## Scheduler-Driven Behaviours (not commands)

### Daily Birthday Check

**Trigger**: APScheduler fires once per day at `CHECK_HOUR:CHECK_MINUTE` in `TIMEZONE`.

**Removal flow** (fires `REMOVE_BEFORE_DAYS` days before birthday):

1. Fetch all employees from Google Sheets (full refresh).
2. For each employee, compute days until next birthday (leap-year safe).
3. If days == `REMOVE_BEFORE_DAYS` and no `birthday_events` record exists for
   `(username, current_year)`:
   - Call `banChatMember` (removes from group).
   - Call `unbanChatMember(only_if_banned=True)` (lifts permanent ban immediately).
   - Insert `birthday_events` record with `status = 'removed'`.
4. Group all employees removed in this run by their shared birthday date and send
   **one combined notification** to the group per unique upcoming date:

   ```
   🎉 Скоро день рождения!

   Через N дней день рождения у:
   ФИО (@username)

   Пожелания:
   <wishes if non-empty>

   Комментарий:
   <comment if non-empty>
   ```

   For multiple employees sharing the same date, list each under the header block.

**Re-removal flow** (FR-005a — fires every day while status = 'removed'):

1. For each `birthday_events` record with `status = 'removed'` where the birthday
   has not yet passed this year:
   - Call `getChatMember` to check current membership.
   - If the employee is a current member → call `banChatMember` + `unbanChatMember`
     again. Log re-removal. No new DB record; no new group notification.

**Restoration flow** (fires `RETURN_AFTER_DAYS` days after birthday):

1. For each `birthday_events` record with `status = 'removed'` where birthday was
   `RETURN_AFTER_DAYS` days ago (or more):
   - Call `unbanChatMember` (re-invite).
   - Update record: `status = 'restored'`, `restored_at = now()`.
   - No group notification sent.

---

## Error Handling Contract

All Telegram API errors during scheduled jobs MUST be caught per-employee and logged
with structured context (`username`, `chat_id`, `error_type`). The job MUST continue
processing remaining employees. Errors do not propagate to crash the scheduler job.

| Error type          | Handling                                                        |
|---------------------|-----------------------------------------------------------------|
| User not found      | Log warning, skip employee for this run                        |
| User never joined   | Log warning, skip employee for this run                        |
| Bot has no rights   | Log error with `can_restrict_members` / `can_invite_users` hint |
| Flood control       | Respect `retry_after`; tenacity retry with exponential backoff  |
| Invalid username    | Log warning, skip employee for this run                        |
| Network/timeout     | tenacity retry up to 3 attempts; log each retry attempt        |
