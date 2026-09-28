from typing import Protocol

from src.conversations.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.conversations.protocols.i_conversation_source import IConversationSource
from src.conversations.protocols.i_source_freshness import ISourceFreshness


class IWhatsAppSource(
    IConversationSource, IConversationDirectory, ISourceFreshness, Protocol
):
    pass
