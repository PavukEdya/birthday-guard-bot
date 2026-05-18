# Feature Specification: Birthday Guard Bot

**Feature Branch**: `001-birthday-guard-bot`

**Created**: 2026-05-18

**Status**: Draft

**Input**: Production-ready Telegram bot that monitors employee birthdays from Google Sheets, automatically removes and restores group members around their birthday, and notifies the group in advance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Birthday Removal & Notification (Priority: P1)

An HR administrator has set up the bot in the company Telegram group. Three days before an employee's birthday, the bot automatically removes that employee from the group and sends a notification so colleagues can prepare a surprise. The employee does not see the preparations.

**Why this priority**: This is the core value proposition — without automated removal and notification, the bot has no purpose.

**Independent Test**: Configure bot with a test user whose birthday is 3 days away; verify the user is removed from the group and a notification message is sent to the group.

**Acceptance Scenarios**:

1. **Given** an employee's birthday is exactly `REMOVE_BEFORE_DAYS` days away, **When** the daily scheduler runs, **Then** the employee is removed from the Telegram group and a notification is posted to the group with the employee's full name, username, wishes, and comment (non-empty fields only).
2. **Given** the employee has already been removed for the current birth year, **When** the scheduler runs again, **Then** no second removal or duplicate notification occurs.
3. **Given** the employee has no wishes or comment in the sheet, **When** the notification is sent, **Then** those empty sections are omitted from the message.

---

### User Story 2 - Automatic Post-Birthday Restoration (Priority: P2)

After the birthday has passed, the bot automatically re-adds the employee to the group without any manual action from administrators.

**Why this priority**: Without automatic restoration, admins must manually re-add employees — defeating the automation purpose.

**Independent Test**: Set `restored_at` to null for a removed employee whose birthday was `RETURN_AFTER_DAYS` days ago; verify the bot re-adds the user and marks them as restored.

**Acceptance Scenarios**:

1. **Given** an employee was removed by the bot and their birthday was `RETURN_AFTER_DAYS` days ago, **When** the daily scheduler runs, **Then** the employee is re-added to the Telegram group.
2. **Given** an employee was already restored, **When** the scheduler runs again, **Then** no second restoration attempt is made.

---

### User Story 3 - Manual Bulk Restoration via /add_all (Priority: P3)

A Telegram group administrator can run `/add_all` to immediately restore all employees currently removed by the bot, without waiting for the automatic schedule.

**Why this priority**: Useful for emergencies (e.g., wrong date in sheet, policy change) but not on the critical path.

**Independent Test**: Remove two test employees via the bot state; admin runs `/add_all`; verify both are re-added and their status is updated.

**Acceptance Scenarios**:

1. **Given** there are employees with `status = removed`, **When** a group admin runs `/add_all`, **Then** all such employees are re-added to the group.
2. **Given** a non-admin user runs `/add_all`, **When** the command is received, **Then** the bot rejects the command silently or with a permission error.
3. **Given** no employees are currently removed, **When** an admin runs `/add_all`, **Then** the bot confirms there is nothing to restore.

---

### Edge Cases

- What happens when a user's Telegram username is invalid or the user has never joined the group?
- What happens when the bot lacks admin rights (`ban_users`, `invite_users`) at the time of action?
- What happens when Telegram rate-limits the bot (flood control)?
- What happens when a Google Sheets row has a malformed birth date or missing required fields?
- What happens for employees born on February 29 in non-leap years?
- What happens when the bot restarts mid-day — will jobs re-run or skip already-processed events?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read employee records daily from a configured Google Sheets document (columns: `tg_username`, `full_name`, `birth_date`, `wishes`, `comment`).
- **FR-002**: The system MUST remove an employee from the Telegram group exactly `REMOVE_BEFORE_DAYS` calendar days before their next birthday.
- **FR-003**: The system MUST send a group notification when an employee is removed, including full name, username, and any non-empty wishes/comment fields.
- **FR-004**: The system MUST restore an employee to the Telegram group `RETURN_AFTER_DAYS` calendar days after their birthday.
- **FR-005**: The system MUST prevent duplicate removals and restorations for the same employee in the same birth year.
- **FR-006**: The system MUST expose a `/add_all` command that immediately restores all bot-removed employees, accessible only to group administrators.
- **FR-007**: The system MUST verify it has the required admin privileges before attempting any removal or restoration action.
- **FR-008**: The system MUST handle gracefully: user not found, user never joined, bot has no rights, flood control, and invalid usernames — logging each error and continuing with remaining employees.
- **FR-009**: The system MUST skip and log Google Sheets rows that fail validation (malformed date, missing required fields) without stopping the daily job.
- **FR-010**: The system MUST correctly handle February 29 birthdays — treating them as March 1 in non-leap years.
- **FR-011**: Birthday comparison MUST ignore the birth year; only month and day matter for scheduling.
- **FR-012**: The scheduler MUST run once per day at a configurable hour and minute in a configurable timezone.
- **FR-013**: Persistent state MUST be maintained across bot restarts to prevent reprocessing already-handled events.

### Key Entities *(include if feature involves data)*

- **Employee**: Represents a staff member tracked in Google Sheets. Key attributes: `tg_username`, `full_name`, `birth_date` (dd.mm.yyyy), `wishes` (optional), `comment` (optional).
- **BirthdayEvent**: Persistent record of a removal/restoration action for a specific employee in a specific year. Key attributes: `username`, `birth_date`, `year`, `removed_at`, `restored_at`, `status` (pending / removed / restored).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The bot processes all employees from the sheet and performs all due removals and restorations within 60 seconds of the daily scheduler firing.
- **SC-002**: Zero duplicate removal or restoration actions occur across any 30-day period of normal operation.
- **SC-003**: The bot recovers from a restart within 30 seconds and resumes scheduled jobs without reprocessing already-handled events.
- **SC-004**: 100% of employees with birthdays falling within the configured window are notified and removed on the correct day (verified over a 1-month test period).
- **SC-005**: Invalid or malformed sheet rows cause no interruption — the job completes for all valid rows and logs a warning for each skipped row.
- **SC-006**: The `/add_all` command completes restoration of all removed employees within 60 seconds of invocation.

## Assumptions

- The Google Sheets document is shared with a Service Account that has read access.
- The bot is already a member of the Telegram group and has admin rights with `ban_users` and `invite_users` permissions before deployment.
- Employee `tg_username` values in the sheet match the actual Telegram usernames used in the group.
- The group is a Telegram supergroup (regular groups do not support `banChatMember`/`unbanChatMember` in the same way).
- The birth date format in Google Sheets is strictly `dd.mm.yyyy`; other formats are treated as invalid.
- The system is deployed on a single instance (no distributed concurrency concerns for the scheduler).
- Network connectivity to Telegram and Google APIs is generally reliable; transient failures are handled by retry logic.
