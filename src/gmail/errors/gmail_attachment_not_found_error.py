from src.gmail.errors.gmail_attachment_error import GmailAttachmentError


class GmailAttachmentNotFoundError(GmailAttachmentError):
    def __init__(self, message_id: str, attachment_id: str) -> None:
        super().__init__(
            f"В письме {message_id} нет вложения {attachment_id}: "
            "возьми attachment_id из read_mail"
        )
        self.message_id = message_id
        self.attachment_id = attachment_id
