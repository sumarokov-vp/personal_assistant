from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


class UiChangedError(DocumentFetchError):
    code = "ui_changed"

    def __init__(self, step: str) -> None:
        super().__init__(
            f"Интерфейс WhatsApp Web изменился: на шаге «{step}» не нашёлся нужный элемент. "
            "Сценарий скачивания надо поправить под новую вёрстку."
        )
        self.step = step
