from logging import getLogger

from telebot.types import CallbackQuery, Chat, Message, Update, User

from .update_trace import UpdateTrace

PRIVATE_CHAT = "private"

logger = getLogger(__name__)


class OwnerUpdateGate:
    def __init__(self, owner_telegram_id: int) -> None:
        self._owner_telegram_id = owner_telegram_id

    def admitted(self, updates: list[Update]) -> list[Update]:
        admitted_updates = []
        for update in updates:
            if self.admits(update):
                admitted_updates.append(update)
            else:
                self._log_dropped(update)
        return admitted_updates

    def admits(self, update: Update) -> bool:
        message: Message | None = update.message
        if message is not None:
            return self._is_owner_in_private_chat(message.from_user, message.chat)
        callback: CallbackQuery | None = update.callback_query
        if callback is not None and callback.message is not None:
            return self._is_owner_in_private_chat(
                callback.from_user, callback.message.chat
            )
        return False

    def _is_owner_in_private_chat(self, sender: User | None, chat: Chat) -> bool:
        return (
            sender is not None
            and sender.id == self._owner_telegram_id
            and chat.type == PRIVATE_CHAT
            and chat.id == self._owner_telegram_id
        )

    def _log_dropped(self, update: Update) -> None:
        trace = UpdateTrace.of(update)
        logger.info(
            "Dropped update: type=%s from=%s chat=%s",
            trace.kind,
            trace.from_id,
            trace.chat_id,
        )
