from src.conversations.errors.attachment_not_found_error import (
    AttachmentNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.attachment_store.protocols.i_attachment_files import (
    IAttachmentFiles,
)
from src.whatsapp.macos_desktop.services.attachment_store.protocols.i_message_lookup import (
    IMessageLookup,
)
from src.whatsapp.macos_desktop.services.attachment_store.protocols.i_remote_media_fetch import (
    IRemoteMediaFetch,
)
from src.whatsapp.macos_desktop.services.entities.chat_title import chat_title
from src.whatsapp.macos_desktop.services.entities.snapshot_key import parse_snapshot_key


class WhatsAppAttachmentStore:
    def __init__(
        self,
        messages: IMessageLookup,
        files: IAttachmentFiles,
        remote: IRemoteMediaFetch,
    ) -> None:
        self._messages = messages
        self._files = files
        self._remote = remote

    def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        attachment = self._files.describe(self._message(message_id))
        return [] if attachment is None else [attachment]

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        row = self._message(message_id)
        attachment = self._files.describe(row)
        if attachment is None or attachment.attachment_id != attachment_id.strip():
            raise AttachmentNotFoundError(message_id, attachment_id)
        local_file = self._files.local_file(row)
        content = (
            self._remote.fetch(row, attachment.name, _desktop_hint(row))
            if local_file is None
            else local_file.read_bytes()
        )
        return AttachmentContent(
            content=content,
            name=attachment.name,
            media_type=attachment.media_type,
        )

    def _message(self, message_id: str) -> WhatsAppMessageRow:
        message_pk = parse_snapshot_key(message_id)
        row = None if message_pk is None else self._messages.by_pk(message_pk)
        if row is None:
            raise MessageNotFoundError(message_id)
        return row


def _desktop_hint(row: WhatsAppMessageRow) -> str:
    title = chat_title(row.chat_title, row.chat_jid, row.chat_pk)
    return (
        f"открой чат «{title}» в WhatsApp Desktop на Mac mini и скачай файл — "
        "он появится у бота со следующим снимком, через несколько минут"
    )
