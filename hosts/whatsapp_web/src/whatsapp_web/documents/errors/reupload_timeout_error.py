from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


class ReuploadTimeoutError(DocumentFetchError):
    code = "reupload_timeout"

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            f"Телефон не перезалил файл за {timeout_seconds:.0f} с — вероятно, он не в сети. "
            "Попробуй позже, когда телефон будет онлайн."
        )
