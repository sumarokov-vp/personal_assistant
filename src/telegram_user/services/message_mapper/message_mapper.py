import mimetypes

from telethon.tl.custom.message import Message
from telethon.tl.types import (
    Document,
    DocumentAttributeFilename,
    MessageMediaDocument,
    MessageMediaPhoto,
    Photo,
    PhotoCachedSize,
    PhotoSize,
    PhotoSizeProgressive,
    PhotoStrippedSize,
)

from src.conversations.models.attachment_availability import AttachmentAvailability
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.message_summary import MessageSummary
from src.telegram_user.models.telegram_chat import TelegramChat
from src.telegram_user.services.entities.chat_profile import display_name
from src.telegram_user.services.entities.message_key import message_key
from src.telegram_user.services.message_mapper.protocols.i_date_display import (
    IDateDisplay,
)

OWNER = "владелец"
UNKNOWN_MEMBER = "участник группы"
SNIPPET_LENGTH = 200
PHOTO_MEDIA_TYPE = "image/jpeg"
UNKNOWN_MEDIA_TYPE = "application/octet-stream"


class MessageMapper:
    def __init__(self, dates: IDateDisplay) -> None:
        self._dates = dates

    def to_summary(self, chat: TelegramChat, message: Message) -> MessageSummary:
        return MessageSummary(
            message_id=message_key(chat.conversation_id, message.id),
            conversation_id=chat.conversation_id,
            title=chat.title,
            sender=self.sender(chat, message),
            date=self._dates.display(message.date),
            snippet=" ".join(self._text(message).split())[:SNIPPET_LENGTH],
            has_attachments=bool(self.attachments(message)),
            link=self._link(chat, message),
        )

    def to_message(self, chat: TelegramChat, message: Message) -> ConversationMessage:
        return ConversationMessage(
            message_id=message_key(chat.conversation_id, message.id),
            conversation_id=chat.conversation_id,
            title=chat.title,
            sender=self.sender(chat, message),
            recipients=self._recipients(chat, message),
            from_owner=bool(message.out),
            date=self._dates.display(message.date),
            text=self._text(message),
            attachments=self.attachments(message),
            link=self._link(chat, message),
        )

    def sender(self, chat: TelegramChat, message: Message) -> str:
        if message.out:
            return OWNER
        if not chat.is_group:
            return chat.title
        return display_name(message.sender) or UNKNOWN_MEMBER

    def attachments(self, message: Message) -> list[ConversationAttachment]:
        media = message.media
        if isinstance(media, MessageMediaDocument) and isinstance(
            media.document, Document
        ):
            return [self._document(media.document)]
        if isinstance(media, MessageMediaPhoto) and isinstance(media.photo, Photo):
            return [self._photo(media.photo)]
        return []

    def _document(self, document: Document) -> ConversationAttachment:
        media_type = document.mime_type or UNKNOWN_MEDIA_TYPE
        return ConversationAttachment(
            attachment_id=str(document.id),
            name=_file_name(document) or _generated_name(document.id, media_type),
            media_type=media_type,
            size=document.size,
            availability=AttachmentAvailability.AVAILABLE,
        )

    def _photo(self, photo: Photo) -> ConversationAttachment:
        return ConversationAttachment(
            attachment_id=str(photo.id),
            name=_generated_name(photo.id, PHOTO_MEDIA_TYPE),
            media_type=PHOTO_MEDIA_TYPE,
            size=max((_photo_size_bytes(size) for size in photo.sizes), default=0),
            availability=AttachmentAvailability.AVAILABLE,
        )

    def _recipients(self, chat: TelegramChat, message: Message) -> str:
        if chat.is_group or message.out:
            return chat.title
        return OWNER

    def _link(self, chat: TelegramChat, message: Message) -> str | None:
        if chat.link_base is None:
            return None
        return f"{chat.link_base}/{message.id}"

    def _text(self, message: Message) -> str:
        return message.message or ""


def _file_name(document: Document) -> str | None:
    for attribute in document.attributes:
        if isinstance(attribute, DocumentAttributeFilename) and attribute.file_name:
            return attribute.file_name
    return None


def _generated_name(media_id: int, media_type: str) -> str:
    extension = mimetypes.guess_extension(media_type) or ""
    return f"telegram_{media_id}{extension}"


def _photo_size_bytes(size: object) -> int:
    if isinstance(size, PhotoSize):
        return size.size
    if isinstance(size, PhotoSizeProgressive):
        return max(size.sizes, default=0)
    if isinstance(size, PhotoCachedSize | PhotoStrippedSize):
        return len(size.bytes)
    return 0
