from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, Message, TelegramObject

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


class AdminCheckMiddleware(BaseMiddleware):
    """Reject /add_all messages from non-administrators."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:  # noqa: ANN401
        if not isinstance(event, Message):
            return await handler(event, data)

        if not event.text or not event.text.startswith("/add_all"):
            return await handler(event, data)

        bot: Bot = data["bot"]
        user = event.from_user
        if user is None:
            return  # no user, silently ignore

        try:
            member = await bot.get_chat_member(event.chat.id, user.id)
            if not isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
                logger.warning(
                    "add_all_rejected",
                    user_id=user.id,
                    username=getattr(user, "username", None),
                )
                return  # silently ignore non-admins
        except Exception as exc:
            logger.error("admin_check_failed", error=str(exc))
            return

        return await handler(event, data)
