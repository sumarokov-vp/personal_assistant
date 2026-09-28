from typing import Protocol

from src.conversations.protocols.i_attachment_store import IAttachmentStore
from src.conversations.protocols.i_conversation_reader import IConversationReader
from src.conversations.protocols.i_message_search import IMessageSearch


class IConversationSource(
    IMessageSearch, IConversationReader, IAttachmentStore, Protocol
):
    pass
