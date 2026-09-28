from src.conversations.models.conversation_message import ConversationMessage
from src.gmail.services.conversation_source.mail_conversation_mapper import (
    MailConversationMapper,
)
from src.gmail.services.conversation_source.protocols.i_gmail_reader import (
    IGmailReader,
)


class GmailMessageReader:
    def __init__(self, reader: IGmailReader) -> None:
        self._reader = reader
        self._mapper = MailConversationMapper()

    def read_message(self, message_id: str) -> ConversationMessage:
        return self._mapper.message(self._reader.get_message(message_id))
