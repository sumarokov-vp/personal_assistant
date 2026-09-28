from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError

NOT_LINKED_DETAIL = (
    "WhatsApp Web не привязан к аккаунту: устройство отвязано на телефоне. "
    "Нужна перепривязка в «Связанные устройства»."
)


class NotLinkedError(DocumentFetchError):
    code = "not_linked"

    def __init__(self, detail: str = NOT_LINKED_DETAIL) -> None:
        super().__init__(detail)
