from ai_framework import Attachment

from src.ai_tools.dropbox_save.chat_attachments.protocols.i_attachment_bytes import (
    IAttachmentBytes,
)
from src.ai_tools.dropbox_save.chat_attachments.protocols.i_chat_history import (
    IChatHistory,
)


class ChatAttachments:
    def __init__(
        self, history: IChatHistory, store: IAttachmentBytes, turns_limit: int
    ) -> None:
        self._history = history
        self._store = store
        self._turns_limit = turns_limit

    def recent(self, thread_id: str) -> list[Attachment]:
        found: list[Attachment] = []
        turns = 0
        for message in reversed(self._history.get_messages(thread_id)):
            if message.role != "user" or message.tool_results:
                continue
            found.extend(
                attachment
                for attachment in reversed(message.attachments or [])
                if attachment.key is not None
            )
            turns += 1
            if turns >= self._turns_limit:
                break
        return found

    def content(self, attachment: Attachment) -> bytes:
        if attachment.key is None:
            raise KeyError(attachment.filename)
        return self._store.get(attachment.key)
