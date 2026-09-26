from logging import getLogger
from pathlib import Path

from ai_framework import Attachment
from ai_framework.entities.attachment import AttachmentMediaType
from bot_framework import (
    BotMessage,
    IDocumentDownloader,
    IMessageReplacer,
    IMessageSender,
    check_message_roles,
)
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.handlers.attachment_limits import (
    IMAGE_TOO_LARGE_TEXT,
    image_exceeds_limit,
)

logger = getLogger(__name__)

TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
TEXT_MIME_TYPES = {"text/plain", "text/markdown", "text/x-markdown", "text/csv"}
ATTACHMENT_MIME_TYPES: dict[str, AttachmentMediaType] = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
    "application/pdf": "application/pdf",
}
ATTACHMENT_EXTENSIONS: dict[str, AttachmentMediaType] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}

UNSUPPORTED_FORMAT_TEXT = "Такой формат пока не читаю."
FILE_TOO_LARGE_TEXT = "Файл больше 10 МБ — такой не читаю."


class DocumentMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        document_downloader: IDocumentDownloader,
        send_to_agent_action: SendToAgentAction,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        role_repo: RoleRepo,
        max_file_bytes: int,
        max_image_bytes: int,
    ) -> None:
        self.document_downloader = document_downloader
        self.send_to_agent_action = send_to_agent_action
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.role_repo = role_repo
        self.max_file_bytes = max_file_bytes
        self.max_image_bytes = max_image_bytes

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        original = message.get_original()
        document = original.document
        if not document:
            return

        file_name = document.file_name or "document"
        caption = original.caption or ""
        extension = Path(file_name).suffix.lower()
        mime_type = (document.mime_type or "").lower()

        if extension in TEXT_EXTENSIONS or mime_type in TEXT_MIME_TYPES:
            if self._refuse_oversized(message, document.file_size or 0, None):
                return
            self._send_text_file(message, document.file_id, file_name, caption)
            return

        media_type = ATTACHMENT_MIME_TYPES.get(mime_type) or ATTACHMENT_EXTENSIONS.get(
            extension
        )
        if media_type is None:
            self.message_sender.send(
                chat_id=message.chat_id, text=UNSUPPORTED_FORMAT_TEXT
            )
            return

        if self._refuse_oversized(message, document.file_size or 0, media_type):
            return
        self._send_attachment(message, document.file_id, file_name, caption, media_type)

    def _send_text_file(
        self, message: BotMessage, file_id: str, file_name: str, caption: str
    ) -> None:
        file_bytes = self.document_downloader.download_document(file_id)
        if self._refuse_oversized(message, len(file_bytes), None):
            return

        content = file_bytes.decode("utf-8-sig", errors="replace")
        agent_text = f"Файл {file_name}:\n\n{content}"
        if caption:
            agent_text = f"{caption}\n\n{agent_text}"
        self._ask_agent(message, agent_text, None)

    def _send_attachment(
        self,
        message: BotMessage,
        file_id: str,
        file_name: str,
        caption: str,
        media_type: AttachmentMediaType,
    ) -> None:
        file_bytes = self.document_downloader.download_document(file_id)
        if self._refuse_oversized(message, len(file_bytes), media_type):
            return

        agent_text = f"Файл {file_name}"
        if caption:
            agent_text = f"{caption}\n\n{agent_text}"
        attachment = Attachment(
            media_type=media_type, filename=file_name, data=file_bytes
        )
        self._ask_agent(message, agent_text, [attachment])

    def _refuse_oversized(
        self, message: BotMessage, size: int, media_type: AttachmentMediaType | None
    ) -> bool:
        if size > self.max_file_bytes:
            self.message_sender.send(chat_id=message.chat_id, text=FILE_TOO_LARGE_TEXT)
            return True
        is_image = media_type is not None and media_type.startswith("image/")
        if is_image and image_exceeds_limit(size, self.max_image_bytes):
            self.message_sender.send(chat_id=message.chat_id, text=IMAGE_TOO_LARGE_TEXT)
            return True
        return False

    def _ask_agent(
        self, message: BotMessage, text: str, attachments: list[Attachment] | None
    ) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        thinking_msg = self.message_sender.send(
            chat_id=message.chat_id, text="Думаю..."
        )
        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                text=text,
                thinking_message_id=thinking_msg.message_id,
                attachments=attachments,
            )
        except Exception as e:
            logger.exception("Agent error on document")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=f"Ошибка: {e}",
            )
