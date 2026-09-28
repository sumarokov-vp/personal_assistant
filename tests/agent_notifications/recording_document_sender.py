from dataclasses import dataclass, field


@dataclass
class SentDocument:
    chat_id: int
    document: bytes
    filename: str


@dataclass
class RecordingDocumentSender:
    sent: list[SentDocument] = field(default_factory=list)

    def send_document(self, chat_id: int, document: bytes, filename: str) -> object:
        self.sent.append(
            SentDocument(chat_id=chat_id, document=document, filename=filename)
        )
        return None
