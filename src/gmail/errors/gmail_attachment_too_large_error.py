from src.gmail.errors.gmail_attachment_error import GmailAttachmentError

BYTES_IN_MB = 1024 * 1024


class GmailAttachmentTooLargeError(GmailAttachmentError):
    def __init__(self, filename: str, size: int, limit: int) -> None:
        super().__init__(
            f"Вложение «{filename}» весит {size / BYTES_IN_MB:.1f} МБ — больше лимита "
            f"{limit // BYTES_IN_MB} МБ, не скачиваю. Открой его в Gmail"
        )
        self.filename = filename
        self.size = size
        self.limit = limit
