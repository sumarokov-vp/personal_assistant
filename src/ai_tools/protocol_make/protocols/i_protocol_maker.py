from typing import Protocol

from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.protocol_maker.protocol_files import ProtocolFiles


class IProtocolMaker(Protocol):
    def make(self, content: ProtocolContent) -> ProtocolFiles: ...
