from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import ChatMemberAdministrator
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger

if TYPE_CHECKING:
    from aiogram import Bot

logger = get_logger(__name__)


class TelegramService:
    def __init__(self, bot: Bot, group_chat_id: int) -> None:
        self._bot = bot
        self._chat_id = group_chat_id

    async def check_bot_is_admin(self) -> bool:
        try:
            bot_user = await self._bot.get_me()
            member = await self._bot.get_chat_member(self._chat_id, bot_user.id)
            if not isinstance(member, ChatMemberAdministrator):
                logger.warning("bot_not_admin", chat_id=self._chat_id)
                return False
            if not member.can_restrict_members:
                logger.warning("bot_lacks_restrict_members", chat_id=self._chat_id)
                return False
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.error("telegram_error", action="check_bot_is_admin", error=str(exc))
            return False

    async def get_chat_member_status(self, username: str) -> str | None:
        """Return the member status string, or None if not found."""
        try:
            member = await self._bot.get_chat_member(self._chat_id, f"@{username}")
            return member.status
        except TelegramBadRequest as exc:
            logger.warning(
                "get_chat_member_failed",
                username=username,
                error=str(exc),
            )
            return None

    async def is_member(self, username: str) -> bool:
        status = await self.get_chat_member_status(username)
        return status in ("member", "administrator", "creator", "restricted")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def ban_and_unban(self, username: str) -> bool:
        """Kick a user without a permanent ban (ban then immediately unban)."""
        try:
            member = await self._bot.get_chat_member(self._chat_id, f"@{username}")
            user_id = member.user.id
        except TelegramBadRequest as exc:
            logger.warning("user_not_found", username=username, error=str(exc))
            return False

        try:
            await self._bot.ban_chat_member(self._chat_id, user_id)
            await self._bot.unban_chat_member(self._chat_id, user_id, only_if_banned=True)
            logger.info("user_removed", username=username, user_id=user_id)
            return True
        except TelegramRetryAfter as exc:
            logger.warning("flood_control", retry_after=exc.retry_after, username=username)
            await asyncio.sleep(exc.retry_after)
            raise
        except TelegramForbiddenError as exc:
            logger.error("telegram_forbidden", username=username, error=str(exc))
            return False
        except TelegramBadRequest as exc:
            logger.warning("telegram_bad_request", username=username, error=str(exc))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def restore_user(self, username: str) -> bool:
        """Re-add a previously removed user to the group."""
        try:
            # Resolve user_id from username — works if user was recently in chat
            member = await self._bot.get_chat_member(self._chat_id, f"@{username}")
            user_id = member.user.id
        except TelegramBadRequest as exc:
            logger.warning("restore_user_not_found", username=username, error=str(exc))
            return False

        try:
            await self._bot.unban_chat_member(self._chat_id, user_id, only_if_banned=False)
            logger.info("user_restored", username=username, user_id=user_id)
            return True
        except TelegramRetryAfter as exc:
            logger.warning("flood_control", retry_after=exc.retry_after, username=username)
            await asyncio.sleep(exc.retry_after)
            raise
        except TelegramBadRequest as exc:
            # User is already in the chat — not an error
            if "user is already" in str(exc).lower():
                logger.info("user_already_in_chat", username=username)
                return True
            logger.warning("restore_bad_request", username=username, error=str(exc))
            return False
        except TelegramForbiddenError as exc:
            logger.error("telegram_forbidden", username=username, error=str(exc))
            return False

    async def send_message(self, text: str) -> None:
        try:
            await self._bot.send_message(self._chat_id, text, parse_mode="HTML")
        except TelegramRetryAfter as exc:
            logger.warning("flood_control_send", retry_after=exc.retry_after)
            await asyncio.sleep(exc.retry_after)
            await self._bot.send_message(self._chat_id, text, parse_mode="HTML")
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.error("send_message_failed", error=str(exc))
