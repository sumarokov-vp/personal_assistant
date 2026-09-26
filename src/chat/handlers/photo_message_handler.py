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
from src.chat.albums.album_buffer import AlbumBuffer
from src.chat.albums.album_photo import AlbumPhoto
from src.chat.albums.protocols.i_timer_factory import ITimerFactory
from src.chat.albums.threading_timer_factory import ThreadingTimerFactory
from src.chat.handlers.attachment_limits import (
    IMAGE_TOO_LARGE_TEXT,
    image_exceeds_limit,
)

logger = getLogger(__name__)

PHOTO_TOO_LARGE_TEXT = "Фото больше 10 МБ — такое не читаю."
TELEGRAM_PHOTO_MEDIA_TYPE: AttachmentMediaType = "image/jpeg"
ALBUM_QUIET_SECONDS = 1.2


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
        timer_factory: ITimerFactory | None = None,
        album_quiet_seconds: float = ALBUM_QUIET_SECONDS,
    ) -> None:
        self.document_downloader = document_downloader
        self.send_to_agent_action = send_to_agent_action
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.role_repo = role_repo
        self.max_file_bytes = max_file_bytes
        self.max_image_bytes = max_image_bytes
        self.album_buffer = AlbumBuffer(
            timer_factory=timer_factory or ThreadingTimerFactory(),
            quiet_seconds=album_quiet_seconds,
            on_album_ready=self._send_album,
        )

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

        caption = original.caption or ""
        if original.media_group_id is None:
            self._send_photos(
                message.chat_id, message.from_user.id, caption, [photo_bytes]
            )
            return

        self.album_buffer.add(
            chat_id=message.chat_id,
            media_group_id=original.media_group_id,
            photo=AlbumPhoto(
                message_id=message.message_id,
                user_id=message.from_user.id,
                caption=caption,
                data=photo_bytes,
            ),
        )

    def _send_album(self, chat_id: int, photos: list[AlbumPhoto]) -> None:
        caption = next((photo.caption for photo in photos if photo.caption), "")
        self._send_photos(
            chat_id, photos[0].user_id, caption, [photo.data for photo in photos]
        )

    def _send_photos(
        self, chat_id: int, user_id: int, caption: str, photos: list[bytes]
    ) -> None:
        thinking_msg = self.message_sender.send(chat_id=chat_id, text="Думаю...")
        try:
            self.send_to_agent_action.execute(
                chat_id=chat_id,
                user_id=user_id,
                text=caption,
                thinking_message_id=thinking_msg.message_id,
                attachments=[
                    Attachment(media_type=TELEGRAM_PHOTO_MEDIA_TYPE, data=data)
                    for data in photos
                ],
            )
        except Exception as e:
            logger.exception("Agent error on photo")
            self.message_replacer.replace(
                chat_id=chat_id,
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
