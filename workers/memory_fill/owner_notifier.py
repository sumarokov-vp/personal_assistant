from bot_framework.core.entities.parse_mode import ParseMode

from workers.memory_fill.protocols.i_plain_message_sender import IPlainMessageSender


class OwnerNotifier:
    def __init__(self, sender: IPlainMessageSender, owner_chat_id: int) -> None:
        self._sender = sender
        self._owner_chat_id = owner_chat_id

    def notify(self, text: str) -> None:
        self._sender.send(
            chat_id=self._owner_chat_id, text=text, parse_mode=ParseMode.PLAIN
        )
