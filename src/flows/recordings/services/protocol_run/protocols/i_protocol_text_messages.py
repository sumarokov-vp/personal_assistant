from typing import Protocol

from src.protocols.models.protocol_content import ProtocolContent


class IProtocolTextMessages(Protocol):
    def messages(self, content: ProtocolContent) -> list[str]: ...
