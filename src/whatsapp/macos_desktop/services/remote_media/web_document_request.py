from datetime import timedelta

from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.core_data_clock.core_data_clock import (
    CORE_DATA_EPOCH,
)
from src.whatsapp.macos_desktop.services.entities.media_kind import (
    DOCUMENT_MESSAGE_TYPE,
)
from src.whatsapp.web_media.models.web_document_request import WebDocumentRequest


def web_document_request(row: WhatsAppMessageRow) -> WebDocumentRequest | None:
    if (
        row.message_type != DOCUMENT_MESSAGE_TYPE
        or not row.chat_jid
        or not row.media_title
        or not row.media_size
    ):
        return None
    sent_at = (
        None
        if row.sent_at is None
        else CORE_DATA_EPOCH + timedelta(seconds=row.sent_at)
    )
    return WebDocumentRequest(
        chat_title=row.chat_title or None,
        chat_jid=row.chat_jid,
        file_name=row.media_title,
        size=row.media_size,
        sent_at=sent_at,
    )
