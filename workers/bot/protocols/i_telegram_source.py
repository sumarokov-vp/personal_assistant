from typing import Protocol

from src.conversations.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.conversations.protocols.i_conversation_source import IConversationSource


class ITelegramSource(IConversationSource, IConversationDirectory, Protocol):
    pass
