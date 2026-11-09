from typing import Protocol

from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.protocol_maker.protocol_document import ProtocolDocument
from src.protocols.services.protocol_maker.protocol_files import ProtocolFiles


class IProtocolDocuments(Protocol):
    def compose(self, content: ProtocolContent) -> ProtocolDocument: ...

    def store(self, document: ProtocolDocument) -> ProtocolFiles: ...
