from logging import getLogger

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

PHOTO_TOO_LARGE_TEXT = "Фото больше 10 МБ — такое не читаю."
TELEGRAM_PHOTO_MEDIA_TYPE: AttachmentMediaType = "image/jpeg"


class PhotoMessageHandler:
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
        if not original.photo:
            return

        largest_photo = original.photo[-1]
        if self._refuse_oversized(message, largest_photo.file_size or 0):
            return

        photo_bytes = self.document_downloader.download_document(largest_photo.file_id)
        if self._refuse_oversized(message, len(photo_bytes)):
            return

        thinking_msg = self.message_sender.send(
            chat_id=message.chat_id, text="Думаю..."
        )
        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                text=original.caption or "",
                thinking_message_id=thinking_msg.message_id,
                attachments=[
                    Attachment(media_type=TELEGRAM_PHOTO_MEDIA_TYPE, data=photo_bytes)
                ],
            )
        except Exception as e:
            logger.exception("Agent error on photo")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=f"Ошибка: {e}",
            )

    def _refuse_oversized(self, message: BotMessage, size: int) -> bool:
        if size > self.max_file_bytes:
            self.message_sender.send(chat_id=message.chat_id, text=PHOTO_TOO_LARGE_TEXT)
            return True
        if image_exceeds_limit(size, self.max_image_bytes):
            self.message_sender.send(chat_id=message.chat_id, text=IMAGE_TOO_LARGE_TEXT)
            return True
        return False
