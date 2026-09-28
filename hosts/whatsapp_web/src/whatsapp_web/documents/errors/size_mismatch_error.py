from whatsapp_web.documents.errors.document_fetch_error import DocumentFetchError


class SizeMismatchError(DocumentFetchError):
    code = "size_mismatch"

    def __init__(self, expected: int, received: list[int]) -> None:
        sizes = ", ".join(str(size) for size in received)
        super().__init__(
            f"Документ с таким именем скачан, но размер не совпал: ждали {expected} Б, получили {sizes} Б."
        )
        self.expected = expected
        self.received = received
