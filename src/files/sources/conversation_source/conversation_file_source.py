from src.conversations.models.conversation_attachment import ConversationAttachment
from src.files.sources.conversation_source.protocols.i_conversation_attachments import (
    IConversationAttachments,
)
from src.files.sources.entities.fetched_file import FetchedFile
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.file_request_incomplete_error import (
    FileRequestIncompleteError,
)
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)


class ConversationFileSource:
    def __init__(
        self, attachments: IConversationAttachments, origin_label: str, max_bytes: int
    ) -> None:
        self._attachments = attachments
        self._origin_label = origin_label
        self._max_bytes = max_bytes

    def fetch(self, request: FileRequest) -> FetchedFile:
        message_id, attachment_id = request.message_id, request.attachment_id
        if not message_id or not attachment_id:
            raise FileRequestIncompleteError(
                "Для вложения переписки нужны message_id и attachment_id "
                "из списка вложений сообщения"
            )
        attachment = self._find(message_id, attachment_id)
        if attachment.size is not None and attachment.size > self._max_bytes:
            raise SourceFileTooLargeError(attachment.name, self._max_bytes)
        fetched = self._attachments.fetch_attachment(message_id, attachment_id)
        if len(fetched.content) > self._max_bytes:
            raise SourceFileTooLargeError(fetched.name, self._max_bytes)
        return FetchedFile(
            content=fetched.content,
            name=fetched.name,
            media_type=fetched.media_type,
            origin=f"{self._origin_label}:{message_id}/{attachment_id}",
        )

    def _find(self, message_id: str, attachment_id: str) -> ConversationAttachment:
        found = next(
            (
                item
                for item in self._attachments.list_attachments(message_id)
                if item.attachment_id == attachment_id
            ),
            None,
        )
        if found is None:
            raise SourceFileNotFoundError(
                f"В сообщении {message_id} нет вложения {attachment_id}: "
                "возьми attachment_id из списка вложений сообщения"
            )
        return found
