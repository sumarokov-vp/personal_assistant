from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)
from src.files.sources.mail_source.protocols.i_mail_attachment import IMailAttachment
from src.files.sources.mail_source.protocols.i_mail_attachments import (
    IMailAttachments,
)


class MailFileSource:
    def __init__(self, mail: IMailAttachments, max_bytes: int) -> None:
        self._mail = mail
        self._max_bytes = max_bytes

    def fetch(self, message_id: str, attachment_id: str) -> FetchedFile:
        attachment = self._find(message_id, attachment_id)
        if attachment.size > self._max_bytes:
            raise SourceFileTooLargeError(attachment.filename, self._max_bytes)
        content = self._mail.get_attachment(message_id, attachment_id)
        if len(content) > self._max_bytes:
            raise SourceFileTooLargeError(attachment.filename, self._max_bytes)
        return FetchedFile(
            content=content, name=attachment.filename, media_type=attachment.media_type
        )

    def _find(self, message_id: str, attachment_id: str) -> IMailAttachment:
        attachments = self._mail.get_message(message_id).attachments
        found = next(
            (item for item in attachments if item.attachment_id == attachment_id),
            None,
        )
        if found is None:
            raise SourceFileNotFoundError(
                f"В письме {message_id} нет вложения {attachment_id}: "
                "возьми attachment_id из read_mail"
            )
        return found
