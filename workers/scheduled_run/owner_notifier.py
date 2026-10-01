from bot_framework import ParseMode

from workers.scheduled_run.protocols.i_plain_sender import IPlainSender
from workers.scheduled_run.protocols.i_text_splitter import ITextSplitter


class SplittingOwnerNotifier:
    def __init__(
        self, sender: IPlainSender, splitter: ITextSplitter, owner_chat_id: int
    ) -> None:
        self._sender = sender
        self._splitter = splitter
        self._owner_chat_id = owner_chat_id

    def notify(self, text: str) -> None:
        for chunk in self._splitter.split(text):
            self._sender.send(
                chat_id=self._owner_chat_id, text=chunk, parse_mode=ParseMode.PLAIN
            )
