from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


class ChatNotFoundError(DocumentFetchError):
    code = "chat_not_found"

    def __init__(self) -> None:
        super().__init__("Чат не нашёлся в WhatsApp Web ни по названию, ни по номеру.")
