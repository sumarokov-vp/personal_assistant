from logging import getLogger
from pathlib import Path

from bot_framework import (
    BotMessage,
    IDocumentDownloader,
    IMessageReplacer,
    IMessageSender,
    check_message_roles,
)
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction

logger = getLogger(__name__)

TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
TEXT_MIME_TYPES = {"text/plain", "text/markdown", "text/x-markdown", "text/csv"}
BINARY_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
BINARY_ATTACHMENT_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

UNSUPPORTED_FORMAT_TEXT = "Такой формат пока не читаю."
FILE_TOO_LARGE_TEXT = "Файл больше 10 МБ — такой не читаю."
BINARY_ATTACHMENTS_NOT_READY_TEXT = "Фото и PDF пока не читаю — скоро научусь."


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
    ) -> None:
        self.document_downloader = document_downloader
        self.send_to_agent_action = send_to_agent_action
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.role_repo = role_repo
        self.max_file_bytes = max_file_bytes

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

        if (document.file_size or 0) > self.max_file_bytes:
            self.message_sender.send(chat_id=message.chat_id, text=FILE_TOO_LARGE_TEXT)
            return

        extension = Path(file_name).suffix.lower()
        mime_type = (document.mime_type or "").lower()

        if extension in TEXT_EXTENSIONS or mime_type in TEXT_MIME_TYPES:
            self._send_text_file(
                message, message.from_user.id, document.file_id, file_name, caption
            )
            return

        if (
            extension in BINARY_ATTACHMENT_EXTENSIONS
            or mime_type in BINARY_ATTACHMENT_MIME_TYPES
        ):
            self._send_binary_attachment(message)
            return

        self.message_sender.send(chat_id=message.chat_id, text=UNSUPPORTED_FORMAT_TEXT)

    def _send_text_file(
        self,
        message: BotMessage,
        user_id: int,
        file_id: str,
        file_name: str,
        caption: str,
    ) -> None:
        file_bytes = self.document_downloader.download_document(file_id)
        if len(file_bytes) > self.max_file_bytes:
            self.message_sender.send(chat_id=message.chat_id, text=FILE_TOO_LARGE_TEXT)
            return

        content = file_bytes.decode("utf-8-sig", errors="replace")
        agent_text = f"Файл {file_name}:\n\n{content}"
        if caption:
            agent_text = f"{caption}\n\n{agent_text}"

        thinking_msg = self.message_sender.send(
            chat_id=message.chat_id,
            text="Думаю...",
        )

        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=user_id,
                text=agent_text,
                thinking_message_id=thinking_msg.message_id,
            )
        except Exception as e:
            logger.exception("Agent error on document")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=f"Ошибка: {e}",
            )

    def _send_binary_attachment(self, message: BotMessage) -> None:
        self.message_sender.send(
            chat_id=message.chat_id,
            text=BINARY_ATTACHMENTS_NOT_READY_TEXT,
        )
