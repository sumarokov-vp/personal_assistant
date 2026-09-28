from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.conversations.errors.attachment_not_found_error import (
    AttachmentNotFoundError,
)
from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.telegram_user.services.attachment_store.protocols.i_attachment_describer import (
    IAttachmentDescriber,
)
from src.telegram_user.services.attachment_store.protocols.i_media_download import (
    IMediaDownload,
)
from src.telegram_user.services.attachment_store.protocols.i_message_locator import (
    IMessageLocator,
)

NOT_DELIVERED_HINT = (
    "Telegram не отдал файл; попроси владельца открыть сообщение в Telegram "
    "и переслать файл боту"
)


class TelegramAttachmentStore:
    def __init__(
        self,
        locator: IMessageLocator,
        describer: IAttachmentDescriber,
        media: IMediaDownload,
    ) -> None:
        self._locator = locator
        self._describer = describer
        self._media = media

    async def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        _, message = await self._locator.locate(message_id)
        return self._describer.attachments(message)

    async def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        _, message = await self._locator.locate(message_id)
        attachment = next(
            (
                item
                for item in self._describer.attachments(message)
                if item.attachment_id == attachment_id.strip()
            ),
            None,
        )
        if attachment is None:
            raise AttachmentNotFoundError(message_id, attachment_id)
        content = await self._media.download(message)
        if content is None:
            raise AttachmentNotDownloadedError(attachment.name, NOT_DELIVERED_HINT)
        return AttachmentContent(
            content=content, name=attachment.name, media_type=attachment.media_type
        )
