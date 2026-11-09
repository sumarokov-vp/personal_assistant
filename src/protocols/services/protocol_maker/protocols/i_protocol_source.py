from typing import Protocol

from src.protocols.models.protocol_content import ProtocolContent


class IProtocolSource(Protocol):
    def document_title(self, content: ProtocolContent) -> str: ...

    def render(self, content: ProtocolContent) -> str: ...
