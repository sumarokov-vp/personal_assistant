from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.message_summary import MessageSummary
from src.whatsapp.macos_desktop.models.whatsapp_message_row import WhatsAppMessageRow
from src.whatsapp.macos_desktop.services.entities.chat_title import (
    chat_title,
    is_group_session,
)
from src.whatsapp.macos_desktop.services.message_mapper.protocols.i_attachment_describer import (
    IAttachmentDescriber,
)
from src.whatsapp.macos_desktop.services.message_mapper.protocols.i_date_display import (
    IDateDisplay,
)

OWNER = "владелец"
UNKNOWN_MEMBER = "участник группы"
SNIPPET_LENGTH = 200


class MessageMapper:
    def __init__(self, dates: IDateDisplay, attachments: IAttachmentDescriber) -> None:
        self._dates = dates
        self._attachments = attachments

    def to_summary(self, row: WhatsAppMessageRow) -> MessageSummary:
        return MessageSummary(
            message_id=str(row.message_pk),
            conversation_id=str(row.chat_pk),
            title=self._title(row),
            sender=self._sender(row),
            date=self._dates.display(row.sent_at),
            snippet=" ".join(row.body.split())[:SNIPPET_LENGTH],
            has_attachments=row.has_attachment,
        )

    def to_message(self, row: WhatsAppMessageRow) -> ConversationMessage:
        attachment = self._attachments.describe(row)
        return ConversationMessage(
            message_id=str(row.message_pk),
            conversation_id=str(row.chat_pk),
            title=self._title(row),
            sender=self._sender(row),
            recipients=self._recipients(row),
            from_owner=row.from_me,
            date=self._dates.display(row.sent_at),
            text=row.body,
            attachments=[] if attachment is None else [attachment],
        )

    def _title(self, row: WhatsAppMessageRow) -> str:
        return chat_title(row.chat_title, row.chat_jid, row.chat_pk)

    def _sender(self, row: WhatsAppMessageRow) -> str:
        if row.from_me:
            return OWNER
        if not is_group_session(row.session_type):
            return self._title(row)
        for name in (row.push_name, row.member_name, row.member_first_name):
            if name:
                return name
        if row.sender_jid:
            return row.sender_jid.split("@", 1)[0]
        return UNKNOWN_MEMBER

    def _recipients(self, row: WhatsAppMessageRow) -> str:
        if is_group_session(row.session_type):
            return self._title(row)
        return self._title(row) if row.from_me else OWNER
